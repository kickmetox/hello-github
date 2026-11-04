import Foundation

enum ProgramGuideService {
    /// Programminfos im TV-Stil (Now/Next + durchscrollbare Leiste).
    static func buildGuide(
        channels: [Channel],
        libraries: [MediaLibrary],
        movies: [Movie],
        now: Date = Date()
    ) -> [ProgramEntry] {
        var entries: [ProgramEntry] = []
        let calendar = Calendar.current

        func slot(_ hoursFromNow: Double, durationHours: Double) -> (Date, Date) {
            let start = now.addingTimeInterval(hoursFromNow * 3600)
            let end = start.addingTimeInterval(durationHours * 3600)
            return (start, end)
        }

        for (index, channel) in channels.prefix(12).enumerated() {
            let offset = Double(index % 3) * -0.4
            let (start, end) = slot(offset, durationHours: 1.0)
            let (nextStart, nextEnd) = (end, end.addingTimeInterval(3600))
            entries.append(
                ProgramEntry(
                    id: StableID.uuid(from: "epg.channel.now.\(channel.key)"),
                    channelName: channel.name,
                    title: channel.nowPlaying ?? "Livestream",
                    synopsis: "Freier Stream · \(channel.category) · \(channel.country)",
                    start: start,
                    end: end,
                    category: channel.category,
                    playableURL: channel.streamURL
                )
            )
            entries.append(
                ProgramEntry(
                    id: StableID.uuid(from: "epg.channel.next.\(channel.key)"),
                    channelName: channel.name,
                    title: "Weiter: \(channel.category)",
                    synopsis: "Nächstes Fenster auf \(channel.name).",
                    start: nextStart,
                    end: nextEnd,
                    category: channel.category,
                    playableURL: channel.streamURL
                )
            )
        }

        let mediathekHighlights: [(String, String, String)] = [
            ("ARD Mediathek", "Abendprogramm & Live", "Öffentlich-rechtliche Highlights in der ARD Mediathek."),
            ("ZDF Mediathek", "Doku & Filme", "Aktuelle Beiträge aus der ZDF Mediathek."),
            ("ARTE", "Themenabend", "Kultur und Gesellschaft auf ARTE."),
            ("phoenix", "Ereignisberichterstattung", "Live und Nachlesen bei phoenix."),
            ("KiKA", "Kinderprogramm", "Serien und Filme für Kinder."),
            ("Deutsche Welle", "DW News", "Internationale Nachrichten live.")
        ]

        for (index, item) in mediathekHighlights.enumerated() {
            let library = libraries.first { $0.name == item.0 }
            let (start, end) = slot(Double(index) * 0.15 - 0.5, durationHours: 1.5)
            entries.append(
                ProgramEntry(
                    id: StableID.uuid(from: "epg.library.\(item.0)"),
                    channelName: item.0,
                    title: item.1,
                    synopsis: item.2,
                    start: start,
                    end: end,
                    category: "Mediathek",
                    deepLink: library?.homeURL
                )
            )
        }

        for (index, movie) in movies.filter({ $0.streamURL != nil }).enumerated() {
            let hour = calendar.component(.hour, from: now)
            let base = calendar.date(bySettingHour: max(hour - 1, 0), minute: 0, second: 0, of: now) ?? now
            let start = base.addingTimeInterval(Double(index) * 45 * 60)
            let end = start.addingTimeInterval(Double(max(movie.durationMinutes, 30)) * 60)
            entries.append(
                ProgramEntry(
                    id: StableID.uuid(from: "epg.movie.\(movie.key)"),
                    channelName: "Freies Kino",
                    title: movie.title,
                    synopsis: "\(movie.genre) · \(movie.license) · \(movie.synopsis)",
                    start: start,
                    end: end,
                    category: "Film",
                    deepLink: movie.infoURL,
                    playableURL: movie.streamURL
                )
            )
        }

        return entries.sorted { $0.start < $1.start }
    }

    static func groupedByChannel(_ entries: [ProgramEntry]) -> [(String, [ProgramEntry])] {
        let grouped = Dictionary(grouping: entries, by: \.channelName)
        return grouped.keys.sorted().map { key in
            (key, (grouped[key] ?? []).sorted { $0.start < $1.start })
        }
    }
}
