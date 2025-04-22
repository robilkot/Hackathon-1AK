using Avalonia.Media.Imaging;
using System.Drawing;

namespace ConveyorCV_frontend.Models
{
    public record StickerParameters(Bitmap Image, PointF Center, SizeF Size, double Rotation);

    public record StickerValidationResult(Bitmap Sticker, bool StickerPresent, bool StickerMatchesDesign, SizeF StickerPosition);
}
