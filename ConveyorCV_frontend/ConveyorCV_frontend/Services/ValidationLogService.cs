using System;
using System.Diagnostics;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia.Animation;
using ConveyorCV_frontend.Models;

namespace ConveyorCV_frontend.Services
{
    public class ValidationLogService
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;
        private readonly JsonSerializerOptions _jsonOptions;

        public event Action<string>? StatusChanged;
        public event Action<string>? ErrorOccurred;

        public ValidationLogService(string baseUrl = "localhost:8000")
        {
            _baseUrl = baseUrl;
            _httpClient = new HttpClient()
            {
                Timeout = TimeSpan.FromSeconds(5)
            };
            _jsonOptions = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            };
        }

        public async Task<ValidationLogResponseDTO?> GetLogsAsync(
            DateTimeOffset? startDate = null,
            DateTimeOffset? endDate = null,
            int page = 1,
            int pageSize = 10)
        {
            try
            {
                var url = $"http://{_baseUrl}/validation/logs?page={page}&page_size={pageSize}";

                if (startDate.HasValue)
                    url += $"&start_date={startDate.Value:yyyy-MM-ddTHH:mm:ss}";

                if (endDate.HasValue)
                    url += $"&end_date={endDate.Value:yyyy-MM-ddTHH:mm:ss}";

                var response = await _httpClient.GetAsync(url);
                response.EnsureSuccessStatusCode();

                var json = await response.Content.ReadAsStringAsync();
                var logs = JsonSerializer.Deserialize<ValidationLogResponseDTO>(json, _jsonOptions);

                return logs;
            }
            catch (Exception ex)
            {
                Debug.WriteLine(ex.Message);
                ErrorOccurred?.Invoke(ex.Message);

                return null;
            }
        }
        
        public async Task<bool> DeleteLogAsync(int logId)
        {
            try
            {
                var response = await _httpClient.DeleteAsync($"http://{_baseUrl}/validation/logs/{logId}");
                response.EnsureSuccessStatusCode();
        
                StatusChanged?.Invoke($"Запись #{logId} удалена");
                return true;
            }
            catch (Exception ex)
            {
                Console.WriteLine(ex.Message);
                ErrorOccurred?.Invoke(ex.Message);

                return false;
            }
        }

        public async Task<ValidationStatisticsDTO?> GetStatisticsAsync(
            DateTimeOffset? startDate = null,
            DateTimeOffset? endDate = null)
        {
            endDate ??= DateTimeOffset.Now;

            try
            {
                var url = $"http://{_baseUrl}/validation/stats";

                url += $"?end_date={endDate.Value:yyyy-MM-ddTHH:mm:ss}";

                if (startDate.HasValue)
                    url += $"&start_date={startDate.Value:yyyy-MM-ddTHH:mm:ss}";


                var response = await _httpClient.GetAsync(url);
                response.EnsureSuccessStatusCode();

                var json = await response.Content.ReadAsStringAsync();
                var logs = JsonSerializer.Deserialize<ValidationStatisticsDTO>(json, _jsonOptions);

                return logs;
            }
            catch (Exception ex)
            {
                Debug.WriteLine(ex.Message);
                ErrorOccurred?.Invoke(ex.Message);

                return null;
            }
        }
    }
}