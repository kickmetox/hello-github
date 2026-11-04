import SwiftUI
import WebKit

struct WebBrowserView: View {
    let title: String
    let url: URL

    var body: some View {
        WebView(url: url)
            .ignoresSafeArea(edges: .bottom)
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Link(destination: url) {
                        Image(systemName: "safari")
                    }
                    .accessibilityLabel("In Safari öffnen")
                }
            }
    }
}

private struct WebView: UIViewRepresentable {
    let url: URL

    func makeUIView(context: Context) -> WKWebView {
        let webView = WKWebView()
        webView.allowsBackForwardNavigationGestures = true
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
