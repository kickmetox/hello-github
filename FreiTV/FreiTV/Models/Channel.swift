import Foundation

struct Channel: Identifiable, Hashable, Codable {
    let id: UUID
    var name: String
    var streamURL: URL
    var category: String
    var logoURL: URL?
    var country: String
    var isFavorite: Bool

    init(
        id: UUID = UUID(),
        name: String,
        streamURL: URL,
        category: String = "Allgemein",
        logoURL: URL? = nil,
        country: String = "International",
        isFavorite: Bool = false
    ) {
        self.id = id
        self.name = name
        self.streamURL = streamURL
        self.category = category
        self.logoURL = logoURL
        self.country = country
        self.isFavorite = isFavorite
    }
}
