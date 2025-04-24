using System.Collections.Generic;
using System.Drawing;
using ConveyorCV_frontend.ViewModels;

namespace ConveyorCV_frontend.Models
{
    public class StickerParametersDTO
    {
        public string Image { get; set; } 
        public float CenterX { get; set; }
        public float CenterY { get; set; }
        public float Width { get; set; }
        public float Height { get; set; } 
        public float Rotation { get; set; }
        
        public static StickerParametersDTO FromViewModel(StickerParametersViewModel vm, string base64Image)
        {
            return new StickerParametersDTO
            {
                Image = base64Image,
                CenterX = (float)vm.Center.X,
                CenterY = (float)vm.Center.Y,
                Width = (float)vm.StickerSize.Width,
                Height = (float)vm.StickerSize.Height,
                Rotation = (float)vm.Rotation
            };
        }
    }
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
