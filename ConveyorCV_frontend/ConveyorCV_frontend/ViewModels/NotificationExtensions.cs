using Avalonia.Notification;
using System;

namespace ConveyorCV_frontend.ViewModels
{
    public static class NotificationExtensions
    {
        public static void Error(this INotificationMessageManager manager, string header, string? body = null)
        {
            var msg = manager
               .CreateMessage()
               .Accent(System.Drawing.Color.Red.ToHex())
               .Background(System.Drawing.Color.Red.ToHex())
               .Foreground("#FFFFFF")
               .HasHeader(header)
               .HasBadge("Ошибка")
               .Animates(true)
               .Dismiss().WithButton("Скрыть", button => { })
               .Dismiss().WithDelay(TimeSpan.FromSeconds(10));

            if (body != null)
            {
                msg.HasMessage(body);
            }

            msg.Queue();
        }
        public static void Success(this INotificationMessageManager manager, string header, string? body = null)
        {
            var msg = manager
               .CreateMessage()
               .Accent("#00cc00")
               .Background("#00cc00")
               .Foreground("#FFFFFF")
               .HasHeader(header)
               .HasBadge("Успех")
               .Animates(true)
               .Dismiss().WithButton("Скрыть", button => { })
               .Dismiss().WithDelay(TimeSpan.FromSeconds(10));

            if (body != null)
            {
                msg.HasMessage(body);
            }

            msg.Queue();
        }

        private static string ToHex(this System.Drawing.Color c)
            => $"#{c.R:X2}{c.G:X2}{c.B:X2}";
    }
}
