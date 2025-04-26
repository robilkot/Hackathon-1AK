using System;
using System.Drawing;

namespace ConveyorCV_frontend.Models
{
    public record StickerValidationParametersDTO(
        byte[] Image,
        PointF StickerCenter,
        SizeF AccSize,
        SizeF StickerSize,
        double StickerRotation
        );

    public record StickerValidationResultDTO(
        byte[] Image,
        DateTimeOffset? Timestamp,
        int? SeqNumber,
        bool? StickerPresent,
        bool? StickerMatchesDesign,
        SizeF? StickerSize,
        PointF? StickerPosition,
        double? StickerRotation
        );
}
