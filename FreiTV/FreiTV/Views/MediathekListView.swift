import SwiftUI

struct MediathekListView: View {
    @ObservedObject var store: MediaStore

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(store.libraryFilters, id: \.self) { filter in
                                Button(filter) { store.libraryFilter = filter }
                                    .font(.subheadline.weight(.semibold))
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 8)
                                    .background(
                                        store.libraryFilter == filter
                                            ? Color(red: 0.15, green: 0.72, blue: 0.78)
                                            : Color(.secondarySystemFill),
                                        in: Capsule()
                                    )
                                    .foregroundStyle(store.libraryFilter == filter ? .white : .primary)
                            }
                        }
                    }
                    .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
                }

                Section {
                    ForEach(store.filteredLibraries) { library in
                        NavigationLink {
                            WebBrowserView(title: library.name, url: library.homeURL)
                        } label: {
                            HStack(spacing: 12) {
                                Image(systemName: iconName(for: library.kind))
                                    .frame(width: 36, height: 36)
                                    .background(Color(.secondarySystemFill), in: RoundedRectangle(cornerRadius: 8))
                                    .foregroundStyle(Color(red: 0.15, green: 0.72, blue: 0.78))

                                VStack(alignment: .leading, spacing: 4) {
                                    Text(library.name).font(.headline)
                                    Text(library.subtitle)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    Text("\(library.kind.rawValue) · \(library.region)")
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                }

                                Spacer()

                                Button {
                                    store.toggleFavorite(library: library)
                                } label: {
                                    Image(systemName: library.isFavorite ? "star.fill" : "star")
                                        .foregroundStyle(library.isFavorite ? .yellow : .secondary)
                                }
                                .buttonStyle(.plain)
                            }
                            .padding(.vertical, 4)
                        }
                    }
                } footer: {
                    Text("\(store.filteredLibraries.count) freie Mediatheken & Kino-Portale · Inhalte der Anbieter")
                }
            }
            .navigationTitle("Mediathek")
            .searchable(text: $store.searchText, prompt: "Mediathek suchen")
        }
    }

    private func iconName(for kind: MediaLibrary.Kind) -> String {
        switch kind {
        case .mediathek: return "play.rectangle.on.rectangle"
        case .livePortal: return "dot.radiowaves.left.and.right"
        case .kino: return "film.stack"
        }
    }
}
