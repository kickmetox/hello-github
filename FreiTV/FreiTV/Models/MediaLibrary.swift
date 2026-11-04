import Foundation

struct MediaLibrary: Identifiable, Hashable, Codable {
    let id: UUID
    let key: String
    var name: String
    var subtitle: String
    var homeURL: URL
    var region: String
    var kind: Kind
    var isFavorite: Bool

    enum Kind: String, Codable, CaseIterable {
        case mediathek = "Mediathek"
        case livePortal = "Live-Portal"
        case kino = "Freies Kino"
    }

    init(
        key: String,
        name: String,
        subtitle: String,
        homeURL: URL,
        region: String = "Deutschland",
        kind: Kind = .mediathek,
        isFavorite: Bool = false
    ) {
        self.id = StableID.uuid(from: "library.\(key)")
        self.key = key
        self.name = name
        self.subtitle = subtitle
        self.homeURL = homeURL
        self.region = region
        self.kind = kind
        self.isFavorite = isFavorite
    }
}
