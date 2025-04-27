using System;

namespace ConveyorCV_frontend.Models
{
#pragma warning disable IDE1006 // Naming Styles
    public enum StreamingMessageType
    {
        RAW = 1,
        SHAPE,
        PROCESSED,
        VALIDATION
    };

    public abstract class StreamingMessageContent;

    public class ImageStreamingMessageContent : StreamingMessageContent
    {
        public required string image { get; set; }

        public byte[] ToImageBytes() => Convert.FromBase64String(image);
    };

    public class ValidationStreamingMessageContent : StreamingMessageContent
    {
        public required StickerValidationResultDTO ValidationResult { get; set; }
    };

    public class StreamingMessageDto
    {
        public StreamingMessageType type { get; set; }
        public required string content { get; set; }
    };

    public class StreamingMessage
    {
        public StreamingMessageType Type { get; set; }
        public required StreamingMessageContent Content { get; set; }
    };
#pragma warning restore IDE1006 // Naming Styles
}