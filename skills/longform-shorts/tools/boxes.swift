import Foundation
import Vision
import AppKit
// 각 이미지의 얼굴·글자 상자를 위쪽 기준 0~1 좌표로 JSON 한 줄씩 출력
func box(_ r: CGRect) -> [Double] { [Double(r.minX), Double(1 - r.maxY), Double(r.width), Double(r.height)] }
for p in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: p), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("{}"); continue }
    let f = VNDetectFaceRectanglesRequest()
    let t = VNRecognizeTextRequest(); t.recognitionLevel = .fast; t.recognitionLanguages = ["ko-KR", "en-US"]
    try? VNImageRequestHandler(cgImage: cg).perform([f, t])
    let faces = (f.results ?? []).map { box($0.boundingBox) }
    let texts: [[String: Any]] = (t.results ?? []).map { ["b": box($0.boundingBox), "s": $0.topCandidates(1).first?.string ?? ""] }
    let o: [String: Any] = ["p": p, "faces": faces, "texts": texts]
    print(String(data: try! JSONSerialization.data(withJSONObject: o), encoding: .utf8)!)
}
