import Foundation

struct Movie: Identifiable, Hashable, Codable {
    let id: UUID
    let key: String
    var title: String
    var year: Int
    var durationMinutes: Int
    var genre: String
    var synopsis: String
    var license: String
    var streamURL: URL?
    var infoURL: URL?
    var isFavorite: Bool

    init(
        key: String,
        title: String,
        year: Int,
        durationMinutes: Int,
        genre: String,
        synopsis: String,
        license: String,
        streamURL: URL? = nil,
        infoURL: URL? = nil,
        isFavorite: Bool = false
    ) {
        self.id = StableID.uuid(from: "movie.\(key)")
        self.key = key
        self.title = title
        self.year = year
        self.durationMinutes = durationMinutes
        self.genre = genre
        self.synopsis = synopsis
        self.license = license
        self.streamURL = streamURL
        self.infoURL = infoURL
        self.isFavorite = isFavorite
    }
}
