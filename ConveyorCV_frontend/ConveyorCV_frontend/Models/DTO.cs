using System;
using System.Drawing;

namespace ConveyorCV_frontend.Models
{
    public record StickerParameters(
        byte[] Image, 
        PointF Center, 
        SizeF Size, 
        double Rotation
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
