import SwiftUI

struct PlaylistSheet: View {
    @ObservedObject var store: MediaStore
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text(
                        "Lade eine öffentlich erlaubte M3U/M3U8-Playlist. Nutze nur Streams, zu deren Empfang du berechtigt bist."
                    )
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                }

                Section("Playlist-URL") {
                    TextField("https://beispiel.de/playlist.m3u", text: $store.playlistURLString)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.URL)
                        .autocorrectionDisabled()

                    Button {
                        Task {
                            await store.loadPlaylist(from: store.playlistURLString)
                        }
                    } label: {
                        if store.isLoadingPlaylist {
                            ProgressView()
                        } else {
                            Label("Playlist laden", systemImage: "arrow.down.circle")
                        }
                    }
                    .disabled(store.isLoadingPlaylist || store.playlistURLString.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }

                if let status = store.statusMessage {
                    Section("Status") {
                        Text(status)
                    }
                }

                Section {
                    Button("Eigene Playlist entfernen", role: .destructive) {
                        store.clearCustomPlaylist()
                    }
                }
            }
            .navigationTitle("Playlist")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Fertig") { dismiss() }
                }
            }
        }
    }
}
