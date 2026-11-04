import SwiftUI

struct AboutView: View {
    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 10) {
                    Text("FreiTV")
                        .font(.largeTitle.bold())
                    Text("Freie Internet-Streams auf dem iPhone – Demo-Kanäle inklusive, eigene M3U-Playlists willkommen.")
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 8)
            }

            Section("Kontakt") {
                LabeledContent("E-Mail") {
                    Link("ame@sellerbach.de", destination: URL(string: "mailto:ame@sellerbach.de")!)
                }
            }

            Section("Hinweise") {
                Text("Eingebaute Kanäle sind öffentliche Demo-/Teststreams.")
                Text("Über „Playlist laden“ kannst du eigene, rechtlich erlaubte M3U-Quellen hinzufügen.")
                Text("Keine Garantie für Verfügbarkeit externer Streams.")
            }

            Section("Technik") {
                LabeledContent("Player", value: "AVKit / HLS")
                LabeledContent("Format", value: "M3U / M3U8")
                LabeledContent("Plattform", value: "iOS 17+")
            }
        }
        .navigationTitle("Über FreiTV")
    }
}
