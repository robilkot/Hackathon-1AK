using Avalonia.Data.Converters;
using System;
using System.Globalization;

namespace ConveyorCV_frontend.Converters
{
    public class StringEqualsConverter : IValueConverter
    {
        public static StringEqualsConverter Instance { get; } = new StringEqualsConverter();

        public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
        {
            if (value == null || parameter == null)
                return false;

            return value.ToString()?.Equals(parameter.ToString(), StringComparison.OrdinalIgnoreCase) ?? false;
        }

        public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}