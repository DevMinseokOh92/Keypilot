using System.IO;
using System.IO.Pipes;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;

namespace KeypilotClient
{
    public partial class MainWindow : Window
    {
        // C++ DLL 연결 (지금은 안 쓰지만 유지)
        [DllImport("KeypilotHook.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern void StartHook();
        [DllImport("KeypilotHook.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern void StopHook();

        public MainWindow()
        {
            InitializeComponent();
            this.Loaded += (s, e) => StartHook();
            this.Closing += (s, e) => StopHook();
        }

        // ★ 버튼 클릭 시 실행되는 함수
        private async void Button_Click(object sender, RoutedEventArgs e)
        {
            string question = InputBox.Text;
            GhostText.Text = "🧠 AI 생각 중...";

            // 비동기로 AI 요청 (화면 안 멈춤)
            string answer = await RequestToPython(question);

            // 결과 출력
            GhostText.Text = answer;
        }

        // ★ 핵심: Named Pipe 통신 로직
        private async Task<string> RequestToPython(string text)
        {
            try
            {
                // 1. 파이프 연결 (서버: keypilot_pipe)
                using (var client = new NamedPipeClientStream(".", "keypilot_pipe", PipeDirection.InOut))
                {
                    await client.ConnectAsync(1000); // 1초 안에 연결 안 되면 포기

                    // 2. 데이터 보내기 (Write)
                    byte[] data = Encoding.UTF8.GetBytes(text);
                    await client.WriteAsync(data, 0, data.Length);

                    // 3. 데이터 받기 (Read)
                    // (Python이 보낼 때까지 기다림)
                    var reader = new StreamReader(client, Encoding.UTF8);
                    string response = await reader.ReadToEndAsync();

                    return response;
                }
            }
            catch (Exception ex)
            {
                return $"❌ Error: Python 서버가 꺼져있나요?\n{ex.Message}";
            }
        }
    }
}