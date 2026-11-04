import Foundation

struct ProgramEntry: Identifiable, Hashable, Codable {
    let id: UUID
    var channelName: String
    var title: String
    var synopsis: String
    var start: Date
    var end: Date
    var category: String
    var deepLink: URL?
    var playableURL: URL?

    var isNow: Bool {
        let now = Date()
        return start <= now && now < end
    }

    var timeLabel: String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "de_DE")
        formatter.dateFormat = "HH:mm"
        return "\(formatter.string(from: start))–\(formatter.string(from: end))"
    }

    init(
        id: UUID = UUID(),
        channelName: String,
        title: String,
        synopsis: String,
        start: Date,
        end: Date,
        category: String,
        deepLink: URL? = nil,
        playableURL: URL? = nil
    ) {
        self.id = id
        self.channelName = channelName
        self.title = title
        self.synopsis = synopsis
        self.start = start
        self.end = end
        self.category = category
        self.deepLink = deepLink
        self.playableURL = playableURL
    }
}
