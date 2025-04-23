using System.Collections.Generic;
using System.Drawing;

namespace ConveyorCV_frontend.Models
{
    public record StickerParameters(byte[] Image, PointF Center, SizeF Size, double Rotation);

    public record StickerValidationResult(byte[] Sticker, bool StickerPresent, bool StickerMatchesDesign, SizeF StickerPosition, SizeF StickerSize);
    public class ValidationResultDTO
    {
        public string Type { get; set; }
        public double Timestamp { get; set; }
        public int SeqNumber { get; set; }
        public bool StickerPresent { get; set; }
        public bool StickerMatchesDesign { get; set; }
        public string Image { get; set; }  // Base64 encoded image
        public Dictionary<string, object> Position { get; set; }
        public Dictionary<string, object> Size { get; set; }
        public double? Rotation { get; set; }
    }
    
}
