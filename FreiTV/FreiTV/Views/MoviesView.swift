import SwiftUI

struct MoviesView: View {
    @ObservedObject var store: MediaStore

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(store.movieGenres, id: \.self) { genre in
                                Button(genre) { store.movieGenreFilter = genre }
                                    .font(.subheadline.weight(.semibold))
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 8)
                                    .background(
                                        store.movieGenreFilter == genre
                                            ? Color(red: 0.15, green: 0.72, blue: 0.78)
                                            : Color(.secondarySystemFill),
                                        in: Capsule()
                                    )
                                    .foregroundStyle(store.movieGenreFilter == genre ? .white : .primary)
                            }
                        }
                    }
                    .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
                }

                Section("Direkt abspielbar") {
                    ForEach(store.filteredMovies.filter { $0.streamURL != nil }) { movie in
                        movieRow(movie)
                    }
                }

                Section("Freies Kino / Sammlungen") {
                    ForEach(store.filteredMovies.filter { $0.streamURL == nil }) { movie in
                        movieRow(movie)
                    }
                }
            }
            .navigationTitle("Kino & Filme")
            .searchable(text: $store.searchText, prompt: "Film suchen")
        }
    }

    @ViewBuilder
    private func movieRow(_ movie: Movie) -> some View {
        NavigationLink {
            if let stream = movie.streamURL {
                StreamPlayerView(title: movie.title, url: stream)
            } else if let info = movie.infoURL {
                WebBrowserView(title: movie.title, url: info)
            } else {
                Text("Keine Quelle verfügbar.")
            }
        } label: {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: movie.streamURL == nil ? "film.stack" : "film")
                    .frame(width: 40, height: 56)
                    .background(
                        LinearGradient(
                            colors: [Color(red: 0.05, green: 0.35, blue: 0.42), Color(red: 0.08, green: 0.12, blue: 0.28)],
                            startPoint: .top,
                            endPoint: .bottom
                        ),
                        in: RoundedRectangle(cornerRadius: 8)
                    )
                    .foregroundStyle(.cyan)

                VStack(alignment: .leading, spacing: 4) {
                    Text(movie.title).font(.headline)
                    Text(metaLine(for: movie))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(movie.synopsis)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(3)
                    Text(movie.license)
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }

                Spacer(minLength: 4)

                Button {
                    store.toggleFavorite(movie: movie)
                } label: {
                    Image(systemName: movie.isFavorite ? "star.fill" : "star")
                        .foregroundStyle(movie.isFavorite ? .yellow : .secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(.vertical, 4)
        }
    }

    private func metaLine(for movie: Movie) -> String {
        var parts: [String] = [movie.genre]
        if movie.year > 0 { parts.append(String(movie.year)) }
        if movie.durationMinutes > 0 { parts.append("\(movie.durationMinutes) Min.") }
        return parts.joined(separator: " · ")
    }
}
