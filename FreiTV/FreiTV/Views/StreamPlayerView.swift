import AVKit
import SwiftUI

struct StreamPlayerView: View {
    let title: String
    let url: URL
    @State private var player: AVPlayer?
    @State private var isBuffering = true
    @State private var errorText: String?

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            if let player {
                VideoPlayer(player: player)
                    .ignoresSafeArea(edges: .bottom)
            }

            if isBuffering {
                ProgressView("Lädt Stream…")
                    .tint(.white)
                    .foregroundStyle(.white)
                    .padding()
                    .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
            }

            if let errorText {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.largeTitle)
                        .foregroundStyle(.orange)
                    Text(errorText)
                        .multilineTextAlignment(.center)
                        .foregroundStyle(.white)
                    Button("Erneut versuchen", action: startPlayback)
                        .buttonStyle(.borderedProminent)
                }
                .padding()
            }
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear(perform: startPlayback)
        .onDisappear {
            player?.pause()
            player = nil
        }
    }

    private func startPlayback() {
        errorText = nil
        isBuffering = true
        let item = AVPlayerItem(url: url)
        let newPlayer = AVPlayer(playerItem: item)
        player = newPlayer
        newPlayer.play()

        NotificationCenter.default.addObserver(
            forName: .AVPlayerItemFailedToPlayToEndTime,
            object: item,
            queue: .main
        ) { notification in
            let error = notification.userInfo?[AVPlayerItemFailedToPlayToEndTimeErrorKey] as? Error
            errorText = error?.localizedDescription ?? "Wiedergabe fehlgeschlagen."
            isBuffering = false
        }

        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 1_200_000_000)
            if item.status == .failed {
                errorText = item.error?.localizedDescription ?? "Stream nicht erreichbar."
            }
            isBuffering = false
        }
    }
}
