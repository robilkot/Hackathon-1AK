using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using ConveyorCV_frontend.Models;

public class StickerParametersService
{
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;
    private readonly JsonSerializerOptions _jsonOptions;

    public event Action<string> ErrorOccurred;
    public event Action<string> StatusChanged;

    public StickerParametersService(string baseUrl = "localhost:8000")
    {
        _baseUrl = baseUrl;
        _httpClient = new HttpClient();
        _jsonOptions = new JsonSerializerOptions();
    }

    public async Task<bool> SetParametersAsync(StickerValidationParametersDTO parameters)
    {
        try
        {
            StatusChanged?.Invoke("Отправка параметров наклейки...");
            
            var json = JsonSerializer.Serialize(parameters, _jsonOptions);
            Console.WriteLine($"Sending parameters: {json}");
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            var response = await _httpClient.PostAsync($"http://{_baseUrl}/sticker/parameters", content);
            response.EnsureSuccessStatusCode();
            
            StatusChanged?.Invoke("Параметры наклейки успешно установлены");
            return true;
        }
        catch (Exception ex)
        {
            var message = $"Ошибка отправки параметров: {ex.Message}";
            Console.WriteLine(message);
            ErrorOccurred?.Invoke(message);
            return false;
        }
    }
    
    public async Task<StickerValidationParametersDTO> GetParametersAsync()
    {
        try
        {
            StatusChanged?.Invoke("Получение параметров наклейки...");
            
            var response = await _httpClient.GetAsync($"http://{_baseUrl}/sticker/parameters");
            response.EnsureSuccessStatusCode();
            
            var json = await response.Content.ReadAsStringAsync();
            var parameters = JsonSerializer.Deserialize<StickerValidationParametersDTO>(json, _jsonOptions);
            Console.WriteLine($"Received parameters: {json}");
            Console.WriteLine($"Received parameters: {parameters}");
            Console.WriteLine($"Image byte array length: {parameters.Image?.Length ?? 0}");
            StatusChanged?.Invoke("Параметры наклейки получены");
            return parameters;
        }
        catch (Exception ex)
        {
            var message = $"Ошибка получения параметров: {ex.Message}";
            Console.WriteLine(message);
            ErrorOccurred?.Invoke(message);
            return null;
        }
    }
    
    public static string ImageToBase64(string imagePath)
    {
        try
        {
            byte[] imageBytes = System.IO.File.ReadAllBytes(imagePath);
            return Convert.ToBase64String(imageBytes);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error converting image to base64: {ex.Message}");
            return null;
        }
    }
}