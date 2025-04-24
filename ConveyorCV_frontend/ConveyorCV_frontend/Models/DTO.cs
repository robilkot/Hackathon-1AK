using System;
using System.Drawing;

namespace ConveyorCV_frontend.Models
{
    public record StickerValidationParameters(
        byte[] Image,
        PointF StickerCenter,
        SizeF AccSize,
        SizeF StickerSize,
        double StickerRotation
        );

    public record StickerValidationResult(
        byte[] Image,
        DateTimeOffset Timestamp,
        int SeqNumber,
        bool StickerPresent,
        bool? StickerMatchesDesign,
        SizeF StickerSize,
        PointF? StickerLocation,
        double? Rotation
        );
}
