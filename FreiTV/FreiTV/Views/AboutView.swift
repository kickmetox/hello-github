import SwiftUI

struct AboutView: View {
    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 10) {
                    Text("FreiTV")
                        .font(.largeTitle.bold())
                    Text("Programmübersicht, freie Mediatheken, Live-Streams und freies Kino – alles an einem Ort.")
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 8)
            }

            Section("Kontakt") {
                LabeledContent("E-Mail") {
                    Link("ame@sellerbach.de", destination: URL(string: "mailto:ame@sellerbach.de")!)
                }
            }

            Section("Inhalte") {
                Text("Programm: durchscrollbare Now/Next-Karten wie im TV.")
                Text("Mediathek: ARD, ZDF, ARTE, 3sat, Dritte, KiKA, funk, ORF, SRF u. a.")
                Text("Kino: Creative-Commons-Filme und freie Archive.")
                Text("Favoriten: sortierbar (manuell, Name, Neueste, Typ).")
            }

            Section("Hinweise") {
                Text("Mediatheken öffnen die offiziellen Portale der Anbieter.")
                Text("Nur rechtlich erlaubte Streams und Playlists verwenden.")
                Text("Keine Garantie für Verfügbarkeit externer Quellen.")
            }

            Section("Technik") {
                LabeledContent("Player", value: "AVKit / HLS / MP4")
                LabeledContent("Mediathek", value: "WKWebView")
                LabeledContent("Format", value: "M3U / M3U8")
                LabeledContent("Plattform", value: "iOS 17+")
            }
        }
        .navigationTitle("Über FreiTV")
    }
}
