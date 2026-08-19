#!/usr/bin/env swift

import AppKit
import Foundation
import Vision

struct FaceBox: Codable {
    let path: String
    let x: Double
    let y: Double
    let width: Double
    let height: Double
    let confidence: Float
}

func largestFace(for path: String) -> FaceBox? {
    let url = URL(fileURLWithPath: path)
    let request = VNDetectFaceRectanglesRequest()
    let handler = VNImageRequestHandler(url: url, options: [:])
    do {
        try handler.perform([request])
    } catch {
        return nil
    }
    guard let observations = request.results, !observations.isEmpty else {
        return nil
    }
    let face = observations.max {
        ($0.boundingBox.width * $0.boundingBox.height) <
        ($1.boundingBox.width * $1.boundingBox.height)
    }!
    let box = face.boundingBox
    return FaceBox(
        path: path,
        x: box.minX,
        y: 1.0 - box.maxY,
        width: box.width,
        height: box.height,
        confidence: face.confidence
    )
}

let boxes = CommandLine.arguments.dropFirst().compactMap { largestFace(for: $0) }
let encoder = JSONEncoder()
encoder.outputFormatting = [.sortedKeys]
if let data = try? encoder.encode(boxes), let output = String(data: data, encoding: .utf8) {
    print(output)
} else {
    fputs("[]\n", stderr)
    exit(2)
}
