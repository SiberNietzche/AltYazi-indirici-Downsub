import json
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from altyazi import translate  # noqa: E402
from altyazi.subtitles import Cue  # noqa: E402


def reply(url, lines):
    text = "\n".join(lines)
    if "clients5" in url:
        return json.dumps([[text, "en"]]).encode()
    return json.dumps([[[text, "x"]]]).encode()


class FakePost:
    """Google Çeviri yerine geçer: gönderilen satırları fn ile dönüştürür ya da hata verir."""

    def __init__(self, fn=None):
        self.calls = []
        self.fn = fn or (lambda lines: ["<" + line + ">" for line in lines])

    def __call__(self, url, body, headers):
        self.calls.append((url, parse_qs(body.decode())["q"][0]))
        result = self.fn(self.calls[-1][1].split("\n"))
        if isinstance(result, Exception):
            raise result
        return reply(url, result)


class GroupingTests(unittest.TestCase):
    def test_pause_and_punctuation_end_sentences(self):
        cues = [Cue(0, 1000, "so today we"), Cue(1000, 2000, "talk about it."), Cue(2000, 3000, "next"),
                Cue(4000, 5000, "after a pause")]
        groups = translate.sentence_groups(cues)
        self.assertEqual([(g.start, g.end) for g in groups], [(0, 1), (2, 2), (3, 3)])
        self.assertEqual(groups[0].text, "so today we talk about it.")

    def test_long_runs_are_cut_at_the_longest_pause(self):
        cues = [Cue(i * 1000, i * 1000 + (900 if i == 3 else 1000), "one two three four five") for i in range(10)]
        groups = translate.sentence_groups(cues)
        self.assertEqual((groups[0].start, groups[0].end), (0, 3))
        self.assertTrue(all(translate._words(g.text) <= translate.MAX_GROUP_WORDS for g in groups))
        self.assertEqual([i for g in groups for i in range(g.start, g.end + 1)], list(range(10)))


class SplitTests(unittest.TestCase):
    def test_split_follows_original_lengths(self):
        parts = translate.split_proportionally("bir iki üç dört beş altı", [10, 10])
        self.assertEqual(parts, ["bir iki üç", "dört beş altı"])

    def test_every_piece_gets_a_word_when_possible(self):
        self.assertEqual(translate.split_proportionally("tek iki", [100, 1, 1]), ["tek", "iki", ""])

    def test_cjk_is_split_by_characters(self):
        self.assertEqual(translate.split_proportionally("你好世界", [5, 5]), ["你好", "世界"])


class TranslatorTests(unittest.TestCase):
    def setUp(self):
        self.sleeps = []

    def translator(self, post):
        return translate.Translator(post, sleep=self.sleeps.append)

    def test_cues_are_translated_in_one_request_and_keep_timing(self):
        post = FakePost()
        cues = [Cue(0, 1000, "hello there"), Cue(1000, 2000, "my friend."), Cue(3000, 4000, "bye")]
        result = self.translator(post).translate_cues(cues, "zh-Hans")
        self.assertEqual(len(post.calls), 1)
        self.assertEqual(parse_qs(urlsplit(post.calls[0][0]).query)["tl"], ["zh-CN"])
        self.assertEqual([(c.start, c.end) for c in result], [(0, 1000), (1000, 2000), (3000, 4000)])
        self.assertEqual(" ".join(c.text for c in result[:2]), "<hello there my friend.>")

    def test_line_count_mismatch_splits_the_batch(self):
        post = FakePost(lambda lines: [" ".join(lines)] if len(lines) > 1 else ["ok:" + lines[0]])
        self.assertEqual(self.translator(post).translate_texts(["a", "b", "c"], "tr"), ["ok:a", "ok:b", "ok:c"])

    def test_large_input_is_batched(self):
        post = FakePost()
        self.assertEqual(len(self.translator(post).translate_texts(["x" * 1000] * 8, "tr")), 8)
        self.assertGreater(len(post.calls), 1)
        self.assertTrue(all(len(q) <= translate.MAX_BATCH_CHARS for _, q in post.calls))

    def test_rate_limit_waits_then_gives_up(self):
        post = FakePost(lambda lines: Exception("HTTP Error 429"))
        with self.assertRaises(translate.TranslateError):
            self.translator(post).translate_texts(["a"], "tr")
        self.assertEqual(len(post.calls), 6)  # İki uç nokta, üç tur
        self.assertIn(5, self.sleeps)
        self.assertIn(15, self.sleeps)

    def test_limited_endpoint_switches_to_the_next_without_waiting(self):
        post = FakePost()
        original = post.fn

        def first_limited(lines):
            return Exception("HTTP Error 429") if "googleapis" in post.calls[-1][0] else original(lines)

        post.fn = first_limited
        translator = self.translator(post)
        self.assertEqual(translator.translate_texts(["a"], "tr"), ["<a>"])
        self.assertEqual(translator.translate_texts(["b"], "tr"), ["<b>"])
        self.assertEqual(["clients5" in url for url, _ in post.calls], [False, True, True])
        self.assertFalse([s for s in self.sleeps if s >= 5])

    def test_rate_limit_recovers(self):
        state = {"n": 0}

        def flaky(lines):
            state["n"] += 1
            return Exception("HTTP Error 503") if state["n"] == 1 else ["ok"]

        self.assertEqual(self.translator(FakePost(flaky)).translate_texts(["a"], "tr"), ["ok"])


if __name__ == "__main__":
    unittest.main()
