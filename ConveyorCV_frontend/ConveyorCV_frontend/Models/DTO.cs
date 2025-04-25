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
        DateTimeOffset Timestamp,
        int SeqNumber,
        bool Sticker_Present,
        bool? Sticker_Matches_Design,
        SizeF Sticker_Size,
        PointF? Sticker_Position,
        double? Sticker_Rotation
        );
}
