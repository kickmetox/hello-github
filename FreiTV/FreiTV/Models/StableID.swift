import Foundation
import CryptoKit

enum StableID {
    /// Deterministische UUID aus einem festen Schlüssel – Favoriten bleiben über App-Starts stabil.
    static func uuid(from key: String) -> UUID {
        let digest = Insecure.MD5.hash(data: Data(key.utf8))
        var bytes = Array(digest)
        bytes[6] = (bytes[6] & 0x0F) | 0x30 // UUID version 3-ish
        bytes[8] = (bytes[8] & 0x3F) | 0x80 // RFC 4122 variant
        return UUID(uuid: (
            bytes[0], bytes[1], bytes[2], bytes[3],
            bytes[4], bytes[5], bytes[6], bytes[7],
            bytes[8], bytes[9], bytes[10], bytes[11],
            bytes[12], bytes[13], bytes[14], bytes[15]
        ))
    }
}
