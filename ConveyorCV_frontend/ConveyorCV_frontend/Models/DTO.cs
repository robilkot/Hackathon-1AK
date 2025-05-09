﻿using System;
using System.Collections.Generic;
using System.Drawing;

namespace ConveyorCV_frontend.Models
{
    public record StickerValidationParametersDTO(
        string StickerDesign, // b64 encoded
        PointF StickerCenter,
        SizeF StickerSize,
        double StickerRotation,
        SizeF AccSize
        );

    public record StickerValidationResultDTO(
        string Image, // b64 encoded
        DateTimeOffset Timestamp,
        int? SeqNumber,
        bool? StickerPresent,
        bool? StickerMatchesDesign,
        SizeF? StickerSize,
        PointF? StickerPosition,
        double? StickerRotation
        );

    public static class DTOExtensions
    {
        public static byte[] ToDecodedBytes(this string b64encodedImage)
            => Convert.FromBase64String(b64encodedImage);

        public static string ToEncodedString(this byte[] b64decodedImage)
            => Convert.ToBase64String(b64decodedImage);
    }
    
    //maybe use default StickerValidationResultDTO, create new for reducing dependencies
    public record ValidationLogItemDTO(
        int Id,
        string? Image, // b64 encoded
        DateTimeOffset Timestamp,
        int SeqNumber,
        bool StickerPresent,
        bool? StickerMatchesDesign,
        PointF? StickerPosition,
        SizeF? StickerSize,
        double? StickerRotation
    )
    {
        public bool IsItemValid => StickerPresent && StickerMatchesDesign!.Value; // todo: is it okay to hold logic here?
    }
    
    public record ValidationLogResponseDTO(
        int Total,
        int Page,
        int PageSize,
        int Pages,
        IEnumerable<ValidationLogItemDTO> Logs
    );

    public record ValidationStatisticsDTO(
        DateTimeOffset StartDate,
        DateTimeOffset EndDate,
        int TotalCount,
        int MissingStickerCount,
        int IncorrectDesignCount
        );
    
    public record CameraSettingsDTO(
        string? PhoneIp,
        int? Port,
        string? VideoPath
    );

    public record ProcessingSettingsDTO(
        int? DownscaleWidth,
        int? DownscaleHeight,
        int? Fps
    );

    public record ValidationSettingsDTO(
        float? PositionTolerancePercent,
        float? RotationToleranceDegrees,
        float? SizeRatioTolerance
    );

    public record DetectionSettingsDTO(
        float? DetectionBorderLeft,
        float? DetectionBorderRight,
        float? DetectionLineHeight
    );

    public record SettingsDTO(
        string? CameraType,
        string? BgPhotoPath,
        string? DatabaseUrl,
        string? StickerParamsFile,
        string? StickerDesignPath,
        string? StickerOutputPath,
        string? SettingsFilePath,
        ProcessingSettingsDTO? Processing,
        CameraSettingsDTO? Camera,
        ValidationSettingsDTO? Validation,
        DetectionSettingsDTO? Detection
    );
}
