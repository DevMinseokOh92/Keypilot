using System.IO;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Threading;
using System.Windows.Input; // Key enum 사용

namespace KeypilotClient
{
    // 데이터 바인딩용 클래스
    public class SuggestionItem
    {
        public string Key { get; set; }  // "F1"
        public string Word { get; set; } // "Hello"
    }

    public partial class MainWindow : Window
    {
        // DLL Import (그대로 유지)
        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        public delegate void KeyCallback(int keyCode);
        [DllImport("KeypilotHook.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern void SetKeyCallback(KeyCallback callback);
        [DllImport("KeypilotHook.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern int StartHook();
        [DllImport("KeypilotHook.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern void StopHook();

        private static KeyCallback? _callbackDelegate;
        private DispatcherTimer? _debounceTimer;
        private StringBuilder _inputBuffer = new StringBuilder();
        private bool _isBusy = false;

        // 현재 추천 목록 저장
        private List<string> _currentSuggestions = new List<string>();
        // AI 요청 시점의 검색어 (Impo 같은 거)
        private string _targetWord = "";

        public MainWindow()
        {
            InitializeComponent();
            SetupTimer();
            this.Loaded += MainWindow_Loaded;
            this.Closing += (s, e) => StopHook();
        }

        private void SetupTimer()
        {
            _debounceTimer = new DispatcherTimer();
            _debounceTimer.Interval = TimeSpan.FromMilliseconds(300);
            _debounceTimer.Tick += async (s, e) => await TriggerAI();
        }

        private void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            try
            {
                _callbackDelegate = new KeyCallback(OnKeyPressed);
                GC.KeepAlive(_callbackDelegate);
                SetKeyCallback(_callbackDelegate);
                StartHook();
                StatusText.Text = "🚀 Ready";
            }
            catch { }
        }

        private void OnKeyPressed(int keyCode)
        {
            System.Windows.Application.Current.Dispatcher.InvokeAsync(() => {
                if (_debounceTimer == null) return;
                _debounceTimer.Stop();

                // F1(112) ~ F12(123) 감지 및 적용
                if (keyCode >= 112 && keyCode <= 123)
                {
                    int index = keyCode - 112; // F1 -> 0, F2 -> 1 ...
                    ApplySuggestion(index);
                    return; // 타이머 시작 안 함
                }

                // 초기화 로직
                if (keyCode == -1 || keyCode == 13) // 마우스클릭 or 엔터
                {
                    ResetState();
                    return;
                }

                if (keyCode == 8) // Backspace
                {
                    if (_inputBuffer.Length > 0) _inputBuffer.Length--;
                }
                else
                {
                    string charToAdd = GetKeyString(keyCode);
                    if (!string.IsNullOrEmpty(charToAdd)) _inputBuffer.Append(charToAdd);
                }

                // 입력 중엔 리스트 숨기기
                SuggestionList.ItemsSource = null;
                _debounceTimer.Start();

            }, System.Windows.Threading.DispatcherPriority.Background);
        }

        // ★ [핵심] 단어 자동 입력 함수
        private void ApplySuggestion(int index)
        {
            if (_currentSuggestions == null || index >= _currentSuggestions.Count) return;

            string selectedWord = _currentSuggestions[index];

            // 1. 기존에 쳤던 글자 지우기 (단어 완성 모드일 때만)
            // _targetWord가 공백이면(다음단어 예측) 지울 필요 없음
            if (!string.IsNullOrWhiteSpace(_targetWord))
            {
                for (int i = 0; i < _targetWord.Length; i++)
                {
                    // Backspace 전송
                    System.Windows.Forms.SendKeys.SendWait("{BACKSPACE}");
                }
            }

            // 2. 새 단어 입력
            System.Windows.Forms.SendKeys.SendWait(selectedWord + " "); // 뒤에 공백 하나 추가

            // 3. 상태 초기화
            ResetState();
        }

        private void ResetState()
        {
            _inputBuffer.Clear();
            _currentSuggestions.Clear();
            SuggestionList.ItemsSource = null;
            StatusText.Text = "🚀 Ready";
        }

        private string GetKeyString(int vkCode)
        {
            if (vkCode >= 65 && vkCode <= 90)
            {
                bool isShift = (System.Windows.Input.Keyboard.Modifiers & System.Windows.Input.ModifierKeys.Shift) == System.Windows.Input.ModifierKeys.Shift;
                string letter = ((char)vkCode).ToString();
                return isShift ? letter : letter.ToLower();
            }
            if (vkCode >= 48 && vkCode <= 57) return ((char)vkCode).ToString();
            if (vkCode == 32) return " ";
            return "";
        }

        private async Task TriggerAI()
        {
            if (_debounceTimer != null) _debounceTimer.Stop();

            // 1. 전체 문장 가져오기 ("My name " 또는 "My nam")
            string currentBuffer = _inputBuffer.ToString();

            // 2. 유효성 검사 (비어있으면 무시)
            if (string.IsNullOrWhiteSpace(currentBuffer)) return;

            // 3. _targetWord 계산 (중요: 이건 나중에 F키 눌렀을 때 '지울 글자 수'를 알기 위함임)
            if (currentBuffer.EndsWith(" "))
            {
                // 공백으로 끝나면? -> 다음 단어 예측 모드 -> 지울 글자 없음
                _targetWord = "";
            }
            else
            {
                // 글자로 끝나면? -> 단어 완성 모드 -> 마지막 단어("nam")를 지워야 함
                _targetWord = currentBuffer.Split(' ').LastOrDefault() ?? "";

                // 단어 완성 모드인데 1글자 미만이면 무시 (너무 짧음)
                if (_targetWord.Length < 1) return;
            }

            if (_isBusy) return;
            _isBusy = true;
            StatusText.Text = "🧠 ...";

            // ★ [핵심 수정] 잘라낸 단어가 아니라, '전체 문장(currentBuffer)'을 보냄!
            // 그래야 AI가 "My name"을 보고 "is"를 추천할 수 있음.
            string jsonResponse = await RequestToPython(currentBuffer);

            try
            {
                var suggestions = JsonSerializer.Deserialize<List<string>>(jsonResponse);

                // 데이터가 비어있으면 UI 클리어
                if (suggestions == null || suggestions.Count == 0)
                {
                    SuggestionList.ItemsSource = null;
                }
                else
                {
                    // UI 바인딩 데이터 생성
                    var uiList = new List<SuggestionItem>();
                    for (int i = 0; i < suggestions.Count; i++)
                    {
                        uiList.Add(new SuggestionItem { Key = $"F{i + 1}", Word = suggestions[i] });
                    }

                    SuggestionList.ItemsSource = uiList;
                    StatusText.Text = "✅ Done";
                }
            }
            catch
            {
                SuggestionList.ItemsSource = null;
            }

            _isBusy = false;
        }

        private async Task<string> RequestToPython(string text)
        {
            try
            {
                using (TcpClient client = new TcpClient())
                {
                    var connectTask = client.ConnectAsync("127.0.0.1", 5000);
                    if (await Task.WhenAny(connectTask, Task.Delay(500)) != connectTask) return "[]";

                    using (NetworkStream stream = client.GetStream())
                    {
                        byte[] data = Encoding.UTF8.GetBytes(text);
                        await stream.WriteAsync(data, 0, data.Length);

                        byte[] buffer = new byte[65536];
                        int bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length);
                        return Encoding.UTF8.GetString(buffer, 0, bytesRead);
                    }
                }
            }
            catch { return "[]"; }
        }
    }
}