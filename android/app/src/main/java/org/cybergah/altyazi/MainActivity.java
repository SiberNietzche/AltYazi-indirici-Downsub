package org.cybergah.altyazi;

import android.Manifest;
import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.view.Gravity;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.ProgressBar;
import android.widget.Toast;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import org.json.JSONObject;

import java.io.File;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Tek ekranlı uygulama: Python motorunu uygulamanın içinde başlatır ve masaüstü programıyla
 * aynı arayüzü bir web görünümünde gösterir. Motor yalnızca 127.0.0.1 üzerinden dinler.
 */
public class MainActivity extends Activity {
    private static final String LOCAL_HOST = "127.0.0.1";
    private static final Pattern LINK = Pattern.compile("https?://\\S+");
    private static final int STORAGE_REQUEST = 1;

    private WebView web;
    private ProgressBar progress;
    private boolean pageReady;
    private String pendingLink;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        FrameLayout layout = new FrameLayout(this);
        layout.setBackgroundColor(Color.rgb(12, 11, 16));
        web = new WebView(this);
        web.setVisibility(View.INVISIBLE);
        web.setBackgroundColor(Color.TRANSPARENT);
        progress = new ProgressBar(this);
        layout.addView(web, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        layout.addView(progress, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.CENTER));
        setContentView(layout);

        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        web.addJavascriptInterface(new Host(), "AndroidHost");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (LOCAL_HOST.equals(uri.getHost())) return false;
                // Uygulamanın kendi sayfası dışındaki bağlantılar tarayıcıda açılır.
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (RuntimeException ignored) {
                    // Bağlantıyı açabilecek uygulama yok
                }
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                pageReady = true;
                progress.setVisibility(View.GONE);
                web.setVisibility(View.VISIBLE);
                deliverLink();
            }
        });

        pendingLink = sharedLink(getIntent());
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R
                && checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
            // Android 10 ve öncesinde İndirilenler klasörü için izin gerekir; yanıt gelince motor başlar.
            requestPermissions(new String[] {Manifest.permission.WRITE_EXTERNAL_STORAGE}, STORAGE_REQUEST);
        } else {
            launchEngine();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == STORAGE_REQUEST) launchEngine();
    }

    private void launchEngine() {
        new Thread(this::startEngine, "engine-start").start();
    }

    /** İndirilenler/AltyaziIndirici; eski Android'de izin verilmediyse uygulamanın kendi klasörü. */
    private File downloadFolder() {
        boolean allowed = Build.VERSION.SDK_INT >= Build.VERSION_CODES.R
                || checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED;
        File base = allowed ? Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS) : getExternalFilesDir(null);
        if (base == null) base = getFilesDir();
        return new File(base, "AltyaziIndirici");
    }

    /** Python'un ve yt-dlp'nin yüklenmesi birkaç saniye sürer; bu yüzden arka planda yapılır. */
    private void startEngine() {
        try {
            if (!Python.isStarted()) Python.start(new AndroidPlatform(getApplicationContext()));
            File data = new File(getFilesDir(), "config");
            File downloads = downloadFolder();
            String url = Python.getInstance().getModule("altyazi.android")
                    .callAttr("start", data.getAbsolutePath(), downloads.getAbsolutePath()).toString();
            runOnUiThread(() -> web.loadUrl(url));
        } catch (RuntimeException error) {
            runOnUiThread(() -> {
                progress.setVisibility(View.GONE);
                Toast.makeText(this, R.string.start_failed, Toast.LENGTH_LONG).show();
            });
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        String link = sharedLink(intent);
        if (link != null) {
            pendingLink = link;
            deliverLink();
        }
    }

    /** "Paylaş" ile gelen metnin içindeki ilk bağlantıyı bulur. */
    private static String sharedLink(Intent intent) {
        if (intent == null || !Intent.ACTION_SEND.equals(intent.getAction())) return null;
        String text = intent.getStringExtra(Intent.EXTRA_TEXT);
        if (text == null) return null;
        Matcher matcher = LINK.matcher(text);
        return matcher.find() ? matcher.group() : null;
    }

    private void deliverLink() {
        if (!pageReady || pendingLink == null) return;
        String script = "window.receiveSharedLink && window.receiveSharedLink(" + JSONObject.quote(pendingLink) + ")";
        pendingLink = null;
        web.evaluateJavascript(script, null);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    /** Sayfanın kullanabildiği tek yerel işlev: "Panodan yapıştır" düğmesi için pano metni. */
    private final class Host {
        @JavascriptInterface
        public String clipboardText() {
            ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            ClipData clip = clipboard == null ? null : clipboard.getPrimaryClip();
            if (clip == null || clip.getItemCount() == 0) return "";
            CharSequence text = clip.getItemAt(0).coerceToText(MainActivity.this);
            return text == null ? "" : text.toString();
        }
    }
}
