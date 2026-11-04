import SwiftUI

struct ContentView: View {
    @StateObject private var store = ChannelStore()
    @State private var showPlaylistSheet = false
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            channelBrowser
                .tabItem { Label("Kanäle", systemImage: "tv") }
                .tag(0)

            favoritesBrowser
                .tabItem { Label("Favoriten", systemImage: "star.fill") }
                .tag(1)

            NavigationStack {
                AboutView()
            }
            .tabItem { Label("Info", systemImage: "info.circle") }
            .tag(2)
        }
        .tint(Color(red: 0.15, green: 0.72, blue: 0.78))
        .sheet(isPresented: $showPlaylistSheet) {
            PlaylistSheet(store: store)
        }
    }

    private var channelBrowser: some View {
        NavigationStack {
            List {
                if !store.categories.isEmpty {
                    Section {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(store.categories, id: \.self) { category in
                                    Button(category) {
                                        store.selectedCategory = category
                                    }
                                    .font(.subheadline.weight(.semibold))
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 8)
                                    .background(
                                        store.selectedCategory == category
                                            ? Color(red: 0.15, green: 0.72, blue: 0.78)
                                            : Color(.secondarySystemFill),
                                        in: Capsule()
                                    )
                                    .foregroundStyle(store.selectedCategory == category ? .white : .primary)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                        .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
                    }
                }

                Section {
                    ForEach(store.filteredChannels) { channel in
                        NavigationLink {
                            PlayerView(channel: channel)
                        } label: {
                            ChannelRow(channel: channel) {
                                store.toggleFavorite(channel)
                            }
                        }
                    }
                } footer: {
                    Text("\(store.filteredChannels.count) Kanäle · Demo-Streams + optionale Playlist")
                }
            }
            .navigationTitle("FreiTV")
            .searchable(text: $store.searchText, prompt: "Kanal suchen")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showPlaylistSheet = true
                    } label: {
                        Image(systemName: "list.bullet.rectangle")
                    }
                    .accessibilityLabel("Playlist laden")
                }
            }
        }
    }

    private var favoritesBrowser: some View {
        NavigationStack {
            Group {
                if store.favoriteChannels.isEmpty {
                    ContentUnavailableView(
                        "Keine Favoriten",
                        systemImage: "star",
                        description: Text("Tippe auf den Stern neben einem Kanal.")
                    )
                } else {
                    List(store.favoriteChannels) { channel in
                        NavigationLink {
                            PlayerView(channel: channel)
                        } label: {
                            ChannelRow(channel: channel) {
                                store.toggleFavorite(channel)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Favoriten")
        }
    }
}

#Preview {
    ContentView()
}
