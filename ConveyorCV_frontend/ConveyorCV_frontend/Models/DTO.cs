using System.Drawing;

namespace ConveyorCV_frontend.Models
{
    public record StickerParameters(byte[] Image, PointF Center, SizeF Size, double Rotation);

    public record StickerValidationResult(byte[] Sticker, bool StickerPresent, bool StickerMatchesDesign, SizeF StickerPosition, SizeF StickerSize);
}
