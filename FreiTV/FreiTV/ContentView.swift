import SwiftUI

struct ContentView: View {
    @StateObject private var store = MediaStore()
    @State private var showPlaylistSheet = false
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            ProgramGuideView(store: store)
                .tabItem { Label("Programm", systemImage: "list.bullet.rectangle.portrait") }
                .tag(0)

            channelBrowser
                .tabItem { Label("Live", systemImage: "tv") }
                .tag(1)

            MediathekListView(store: store)
                .tabItem { Label("Mediathek", systemImage: "play.rectangle.on.rectangle") }
                .tag(2)

            MoviesView(store: store)
                .tabItem { Label("Kino", systemImage: "film") }
                .tag(3)

            FavoritesView(store: store)
                .tabItem { Label("Favoriten", systemImage: "star.fill") }
                .tag(4)

            NavigationStack {
                AboutView()
            }
            .tabItem { Label("Info", systemImage: "info.circle") }
            .tag(5)
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
                            StreamPlayerView(title: channel.name, url: channel.streamURL)
                        } label: {
                            ChannelRow(channel: channel) {
                                store.toggleFavorite(channel: channel)
                            }
                        }
                    }
                } footer: {
                    Text("\(store.filteredChannels.count) Live-/Demo-Kanäle · eigene M3U möglich")
                }
            }
            .navigationTitle("Live")
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
}

#Preview {
    ContentView()
}
