import Foundation

struct Channel: Identifiable, Hashable, Codable {
    let id: UUID
    let key: String
    var name: String
    var streamURL: URL
    var category: String
    var logoURL: URL?
    var country: String
    var nowPlaying: String?
    var isFavorite: Bool

    init(
        key: String? = nil,
        name: String,
        streamURL: URL,
        category: String = "Allgemein",
        logoURL: URL? = nil,
        country: String = "International",
        nowPlaying: String? = nil,
        isFavorite: Bool = false
    ) {
        let stableKey = key ?? streamURL.absoluteString
        self.key = stableKey
        self.id = StableID.uuid(from: "channel.\(stableKey)")
        self.name = name
        self.streamURL = streamURL
        self.category = category
        self.logoURL = logoURL
        self.country = country
        self.nowPlaying = nowPlaying
        self.isFavorite = isFavorite
    }
}
