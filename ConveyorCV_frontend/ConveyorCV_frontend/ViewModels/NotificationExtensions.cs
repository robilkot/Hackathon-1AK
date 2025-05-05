using System;
using Avalonia.Notification;

namespace ConveyorCV_frontend.ViewModels
{
    public static class NotificationExtensions
    {
        private static DateTime _lastNotificationTime = DateTime.MinValue;
        private static string _lastMessage = string.Empty;

        public static void Success(this INotificationMessageManager manager, string header, string? body = null)
        {
            if (DateTime.Now - _lastNotificationTime < TimeSpan.FromSeconds(1) && 
                _lastMessage == $"{header}:{body}")
                return;
                
            _lastNotificationTime = DateTime.Now;
            _lastMessage = $"{header}:{body}";
            
            try
            {
                var message = manager.CreateMessage();
                
                message.Accent("#00cc00")
                    .Background("#00cc00")
                    .Foreground("#FFFFFF")
                    .HasHeader(header)
                    .HasBadge("Успех")
                    .Animates(true)
                    .Dismiss().WithButton("Скрыть", button => { })
                    .Dismiss().WithDelay(TimeSpan.FromSeconds(3));

                if (!string.IsNullOrEmpty(body))
                {
                    message.HasMessage(body);
                }

                message.Queue();
            }
            catch (Exception) 
            {
                // Silently catch notification errors to prevent app crashes
            }
        }

        public static void Error(this INotificationMessageManager manager, string header, string? body = null)
        {
            if (DateTime.Now - _lastNotificationTime < TimeSpan.FromSeconds(1) && 
                _lastMessage == $"{header}:{body}")
                return;
                
            _lastNotificationTime = DateTime.Now;
            _lastMessage = $"{header}:{body}";
            
            try
            {
                var message = manager.CreateMessage();
                
                message  .Accent(System.Drawing.Color.Red.ToHex())
                    .Background(System.Drawing.Color.Red.ToHex())
                    .Foreground("#FFFFFF")
                    .HasHeader(header)
                    .HasBadge("Ошибка")
                    .Animates(true)
                    .Dismiss().WithButton("Скрыть", button => { })
                    .Dismiss().WithDelay(TimeSpan.FromSeconds(5));

                if (!string.IsNullOrEmpty(body))
                {
                    message.HasMessage(body);
                }

                message.Queue();
            }
            catch (Exception) 
            {
                // Silently catch notification errors to prevent app crashes
            }
        }

        private static string ToHex(this System.Drawing.Color c)
            => $"#{c.R:X2}{c.G:X2}{c.B:X2}";
    }
}