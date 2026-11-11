fn main() {
    // Kabuğun kendi komutları da izin listesine girer; böylece capabilities/default.json içinde
    // açıkça izin verilmeyen hiçbir komut arayüzden çağrılamaz.
    let attributes = tauri_build::Attributes::new()
        .app_manifest(tauri_build::AppManifest::new().commands(&["choose_folder"]));
    tauri_build::try_build(attributes).expect("Tauri derleme adımı başarısız");
}
