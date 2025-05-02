using Avalonia.Data.Converters;
using ConveyorCV_frontend.Models;
using System;
using System.Collections.Generic;
using System.Globalization;

namespace ConveyorCV_frontend.Converters
{
    public class StreamStatusToTextConverter : IValueConverter
    {
        private static readonly Dictionary<StreamStatus, string> _dict = new() {
            { StreamStatus.Disconnected, "Отключено"},
            { StreamStatus.Connecting, "Подключение..."},
            { StreamStatus.Starting, "Запуск трансляции..."},
            { StreamStatus.Running, "Подключено"},
            { StreamStatus.Stopping, "Отключение..."},
            };
        public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
        {
            if (value is StreamStatus status)
            {
                return _dict[status];
            }
            return null;
        }

        public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}
