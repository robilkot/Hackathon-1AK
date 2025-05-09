﻿using Avalonia.Controls;
using Avalonia.Media.Imaging;
using ConveyorCV_frontend.Models;
using ConveyorCV_frontend.Services;
using ReactiveUI;
using System;
using System.Diagnostics;
using System.IO;

namespace ConveyorCV_frontend.ViewModels
{
    public class StickerValidationResultViewModel : ViewModelBase
    {
        private StickerValidationResultDTO? _lastResult;
        public StickerValidationResultDTO? LastResult
        {
            get => _lastResult;
            set
            {
                this.RaiseAndSetIfChanged(ref _lastResult, value);

                if (value != null)
                {
                    StickerPresent = value.StickerPresent ?? false;
                    StickerMatchesDesign = value.StickerMatchesDesign;
                    StickerLocation = value.StickerPosition.HasValue ? new(value.StickerPosition.Value) : null;
                    StickerSize = value.StickerSize.HasValue ? new(value.StickerSize.Value) : null;
                    Rotation = value.StickerRotation;
                    SeqNumber = value.SeqNumber ?? 0;
                    Timestamp = value.Timestamp;

                    if (!Design.IsDesignMode)
                    {
                        using var ms = new MemoryStream(value.Image.ToDecodedBytes());
                        Image = new Bitmap(ms);
                    }
                }
            }
        }

        private Bitmap? _image;
        public Bitmap? Image
        {
            get => _image;
            set => this.RaiseAndSetIfChanged(ref _image, value);
        }

        private bool _stickerPresent;
        public bool StickerPresent
        {
            get => _stickerPresent;
            set => this.RaiseAndSetIfChanged(ref _stickerPresent, value);
        }

        private bool? _stickerMatchesDesign;
        public bool? StickerMatchesDesign
        {
            get => _stickerMatchesDesign;
            set => this.RaiseAndSetIfChanged(ref _stickerMatchesDesign, value);
        }

        private PointViewModel? _stickerLocation = new(300f, 200f);
        public PointViewModel? StickerLocation
        {
            get => _stickerLocation;
            set => this.RaiseAndSetIfChanged(ref _stickerLocation, value);
        }

        private SizeViewModel? _stickerSize = new(400f, 200f);
        public SizeViewModel? StickerSize
        {
            get => _stickerSize;
            set => this.RaiseAndSetIfChanged(ref _stickerSize, value);
        }

        private double? _rotation = 5;
        public double? Rotation
        {
            get => _rotation;
            set => this.RaiseAndSetIfChanged(ref _rotation, value);
        }

        private int _seqNumber = 42;
        public int SeqNumber
        {
            get => _seqNumber;
            set => this.RaiseAndSetIfChanged(ref _seqNumber, value);
        }

        private DateTimeOffset _timestamp = DateTimeOffset.UtcNow;
        public DateTimeOffset Timestamp
        {
            get => _timestamp;
            set => this.RaiseAndSetIfChanged(ref _timestamp, value);
        }

        public StickerValidationResultViewModel() : this(null) { }

        public StickerValidationResultViewModel(WebSocketService? webSocketService = null)
        {
            if(webSocketService is not null)
            {
                webSocketService.MessageReceived += WebSocketService_MessageReceived;
            }

            if (Design.IsDesignMode)
            {
                LastResult = new("", new(), 0, true, false, new(), new(), 5);
                Timestamp = DateTimeOffset.UtcNow;
            }
        }

        private void WebSocketService_MessageReceived(StreamingMessage obj)
        {
            if (obj.Content is not ValidationStreamingMessageContent validationMessage)
                return;

            LastResult = validationMessage.ValidationResult;
        }
    }
}