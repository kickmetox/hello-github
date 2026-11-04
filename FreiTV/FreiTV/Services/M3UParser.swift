import Foundation

enum M3UParser {
    static func parse(_ text: String) -> [Channel] {
        let lines = text
            .replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\r", with: "\n")
            .components(separatedBy: "\n")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

        var channels: [Channel] = []
        var pendingName = "Unbekannt"
        var pendingLogo: URL?
        var pendingCategory = "Playlist"
        var pendingCountry = "International"

        for line in lines {
            if line.hasPrefix("#EXTINF:") {
                pendingName = extractName(from: line)
                pendingLogo = extractAttribute(named: "tvg-logo", from: line).flatMap(URL.init(string:))
                pendingCategory = extractAttribute(named: "group-title", from: line) ?? "Playlist"
                pendingCountry = extractAttribute(named: "tvg-country", from: line) ?? "International"
            } else if line.hasPrefix("#") {
                continue
            } else if let url = URL(string: line), url.scheme == "http" || url.scheme == "https" {
                channels.append(
                    Channel(
                        name: pendingName,
                        streamURL: url,
                        category: pendingCategory,
                        logoURL: pendingLogo,
                        country: pendingCountry
                    )
                )
                pendingName = "Unbekannt"
                pendingLogo = nil
                pendingCategory = "Playlist"
                pendingCountry = "International"
            }
        }

        return channels
    }

    private static func extractName(from line: String) -> String {
        if let comma = line.firstIndex(of: ",") {
            let name = String(line[line.index(after: comma)...]).trimmingCharacters(in: .whitespacesAndNewlines)
            return name.isEmpty ? "Unbekannt" : name
        }
        return "Unbekannt"
    }

    private static func extractAttribute(named key: String, from line: String) -> String? {
        let pattern = #"\#(key)="([^"]*)""#
        guard let regex = try? NSRegularExpression(pattern: pattern) else { return nil }
        let range = NSRange(line.startIndex..<line.endIndex, in: line)
        guard let match = regex.firstMatch(in: line, range: range),
              let valueRange = Range(match.range(at: 1), in: line) else {
            return nil
        }
        let value = String(line[valueRange]).trimmingCharacters(in: .whitespacesAndNewlines)
        return value.isEmpty ? nil : value
    }
}
