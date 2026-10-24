using System;
using System.Globalization;
using UnityEngine;
using UnityEngine.UI;

namespace ManakaDGLab.Telemetry
{
    // Native game canvas: resolution/window/fullscreen independent, display only.
    internal static class CustomHudCanvas
    {
        private const int Samples = 32;
        private sealed class Cell {
            internal GameObject Root;
            internal Text Title, Number, State;
            internal RectTransform Graph;
            internal Image[] Lines;
            internal Image[] Bars;
            internal float[] History = new float[Samples];
        }
        private static GameObject _root, _panel;
        private static Image _background;
        private static readonly Cell[] Cells = new Cell[4];
        private static float _nextDraw, _nextSample;
        private static bool _wasVisible;
        private static string _layout = "";
        private static readonly Color Pink = new Color(1f, .27f, .65f, .98f);
        private static readonly Color Lilac = new Color(.79f, .66f, 1f, .98f);

        internal static void Tick()
        {
            HudStatus status = HudStatusReceiver.Snapshot();
            bool visible = status.Visible && Environment.TickCount64 - status.ReceivedAt <= 1000;
            if (_root == null && !visible) return;
            EnsureCreated();
            if (_panel == null) return;
            if (_panel.activeSelf != visible) _panel.SetActive(visible);
            if (!visible) { _wasVisible = false; return; }
            if (!_wasVisible) {
                foreach (Cell cell in Cells) Array.Clear(cell.History, 0, Samples);
                _wasVisible = true;
            }
            // Match the 30 FPS control-center preview without per-game-frame work.
            if (Time.unscaledTime < _nextDraw) return;
            _nextDraw = Time.unscaledTime + 1f / 30f;
            RectTransform canvas = _root.GetComponent<RectTransform>();
            if (canvas == null || canvas.rect.width <= 1 || canvas.rect.height <= 1) return;
            string layout = status.Flags + ":" + status.Scale + ":" + status.Opacity + ":" + status.Anchor + ":" + status.X + ":" + status.Y + ":" + Screen.width + ":" + Screen.height + ":" + canvas.rect.width + ":" + canvas.rect.height;
            if (_layout != layout) { Layout(status, canvas.rect.width, canvas.rect.height); _layout = layout; }
            bool sample = Time.unscaledTime >= _nextSample;
            if (sample) _nextSample = Time.unscaledTime + .1f;
            for (int i = 0; i < 4; i++) {
                Cell cell = Cells[i];
                if (!cell.Root.activeSelf) continue;
                int role = i < 2 ? 1 : 2;
                bool connected = (status.Connections & role) != 0;
                bool active = connected && (status.Activities & role) != 0;
                Color color = i % 2 == 0 ? Pink : Lilac;
                Color inactive = new Color(.62f, .56f, .68f, .8f);
                cell.Number.text = Mathf.RoundToInt(active ? status.Strengths[i] : 0).ToString(CultureInfo.InvariantCulture);
                cell.Number.color = active ? Color.white : inactive;
                cell.State.text = !connected ? "OFFLINE" : active ? "SYNC" : "IDLE";
                cell.State.color = active ? color : inactive;
                if (sample) {
                    for (int j = 1; j < Samples; j++) cell.History[j - 1] = cell.History[j];
                    cell.History[Samples - 1] = active ? status.Pulses[i] : 0;
                }
                if (cell.Graph.gameObject.activeSelf && sample) Draw(cell, active ? color : inactive);
                float ratio = active && status.Caps[i] > 0 ? status.Strengths[i] / status.Caps[i] : 0;
                for (int bar = 0; bar < 5; bar++)
                    cell.Bars[bar].color = ratio > bar / 5f ? color : new Color(color.r, color.g, color.b, .13f);
            }
        }

        private static bool Has(HudStatus status, int flag) { return (status.Flags & flag) != 0; }

        private static void Layout(HudStatus status, float viewWidth, float viewHeight)
        {
            int count = 0;
            for (int i = 0; i < 4; i++) {
                bool shown = Has(status, i < 2 ? 1 : 2) && Has(status, i % 2 == 0 ? 4 : 8);
                Cells[i].Root.SetActive(shown);
                if (shown) count++;
            }
            float scale = status.Scale / 100f;
            float width = Mathf.Min(Mathf.Max(80, viewWidth - 24), Mathf.Max(1, count) * 174f * scale);
            float height = Mathf.Min(Mathf.Max(30, viewHeight - 24), 72f * scale);
            if (status.Anchor == 0) width = Mathf.Min(width, Mathf.Max(80, viewWidth * .59f - 24));
            float left = Mathf.Min(viewWidth * .21f, viewWidth * .59f - width - 12);
            float top = viewHeight - 24 - height;
            if (status.Anchor == 7) {
                left = (viewWidth - width) * status.X / 100f;
                top = (viewHeight - height) * status.Y / 100f;
            } else if (status.Anchor > 0) {
                int horizontal = (status.Anchor - 1) % 3;
                left = horizontal == 0 ? 12 : horizontal == 1 ? (viewWidth - width) / 2 : viewWidth - width - 12;
                top = status.Anchor <= 3 ? 24 : viewHeight - height - 24;
            }
            left = Mathf.Clamp(left, 0, Mathf.Max(0, viewWidth - width));
            top = Mathf.Clamp(top, 0, Mathf.Max(0, viewHeight - height));
            Set(_background.rectTransform, new Vector2(0, 1), new Vector2(0, 1), new Vector2(0, 1), new Vector2(left, -top), new Vector2(width, height));
            _background.color = new Color(.08f, .025f, .08f, status.Opacity / 100f);
            int index = 0;
            for (int i = 0; i < 4; i++) {
                Cell cell = Cells[i];
                if (!cell.Root.activeSelf) continue;
                Set(cell.Root.GetComponent<RectTransform>(), new Vector2(index / (float)count, 0), new Vector2((index + 1) / (float)count, 1), new Vector2(.5f, .5f), Vector2.zero, new Vector2(-10, -8));
                cell.Title.fontSize = Mathf.Max(8, Mathf.RoundToInt(12 * scale));
                cell.Number.fontSize = Mathf.Max(10, Mathf.RoundToInt(16 * scale));
                cell.State.fontSize = Mathf.Max(7, Mathf.RoundToInt(8 * scale));
                cell.Number.gameObject.SetActive(Has(status, 16));
                cell.State.gameObject.SetActive(Has(status, 32));
                bool graph = i < 2 && Has(status, 64);
                cell.Graph.gameObject.SetActive(graph);
                foreach (Image bar in cell.Bars) bar.gameObject.SetActive(!graph);
                index++;
            }
        }

        private static void EnsureCreated()
        {
            if (_root != null) return;
            try {
                _root = new GameObject("ManakaCustomHud");
                UnityEngine.Object.DontDestroyOnLoad(_root);
                Canvas canvas = _root.AddComponent<Canvas>();
                canvas.renderMode = RenderMode.ScreenSpaceOverlay;
                canvas.sortingOrder = 32000;
                CanvasScaler scaler = _root.AddComponent<CanvasScaler>();
                scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
                scaler.referenceResolution = new Vector2(1920, 1080);
                scaler.matchWidthOrHeight = .5f;
                _background = Image("Panel", _root.transform, Color.clear);
                _panel = _background.gameObject;
                Image top = Image("RoseRule", _panel.transform, new Color(1, .25f, .6f, .6f));
                Set(top.rectTransform, new Vector2(0, 1), new Vector2(1, 1), new Vector2(.5f, 1), Vector2.zero, new Vector2(0, 1));
                Image bottom = Image("SilverRule", _panel.transform, new Color(.85f, .7f, .9f, .24f));
                Set(bottom.rectTransform, Vector2.zero, new Vector2(1, 0), new Vector2(.5f, 0), Vector2.zero, new Vector2(0, 1));
                Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
                for (int i = 0; i < 4; i++) {
                    Cell cell = new Cell(); Cells[i] = cell;
                    Color color = i % 2 == 0 ? Pink : Lilac;
                    cell.Root = Image("Cell" + i, _panel.transform, Color.clear).gameObject;
                    Transform parent = cell.Root.transform;
                    Image rule = Image("ChannelRule", parent, color);
                    Set(rule.rectTransform, Vector2.zero, new Vector2(0, 1), new Vector2(0, .5f), Vector2.zero, new Vector2(2, 0));
                    cell.Title = Text("Title", parent, (i % 2 == 0 ? "A" : "B") + (i < 2 ? " / PULSE" : " / OVC"), font, 12, color);
                    Set(cell.Title.rectTransform, new Vector2(.05f, .68f), new Vector2(.76f, 1), new Vector2(0, .5f), Vector2.zero, Vector2.zero);
                    cell.Number = Text("Strength", parent, "0", font, 16, Color.white);
                    cell.Number.alignment = TextAnchor.MiddleRight;
                    Set(cell.Number.rectTransform, new Vector2(.76f, .66f), new Vector2(.96f, 1), new Vector2(1, .5f), Vector2.zero, Vector2.zero);
                    cell.State = Text("State", parent, "IDLE", font, 8, color);
                    Set(cell.State.rectTransform, new Vector2(.05f, 0), new Vector2(.45f, .22f), new Vector2(0, .5f), Vector2.zero, Vector2.zero);
                    cell.Graph = Image("Graph", parent, Color.clear).rectTransform;
                    Set(cell.Graph, new Vector2(.05f, .24f), new Vector2(.95f, .65f), new Vector2(.5f, .5f), Vector2.zero, Vector2.zero);
                    cell.Lines = new Image[i < 2 ? Samples - 1 : 0];
                    for (int j = 0; j < cell.Lines.Length; j++) {
                        cell.Lines[j] = Image("Segment" + j, cell.Graph, color);
                        Set(cell.Lines[j].rectTransform, new Vector2(.5f, .5f), new Vector2(.5f, .5f), new Vector2(0, .5f), Vector2.zero, Vector2.zero);
                    }
                    cell.Bars = new Image[5];
                    for (int j = 0; j < 5; j++) {
                        cell.Bars[j] = Image("Bar" + j, parent, color);
                        Set(cell.Bars[j].rectTransform, new Vector2(.53f + j * .08f, .1f), new Vector2(.58f + j * .08f, .25f + j * .07f), new Vector2(.5f, 0), Vector2.zero, Vector2.zero);
                    }
                }
                _layout = ""; _panel.SetActive(false);
            } catch (Exception error) { Plugin.PluginLog.LogError("Custom HUD: " + error.Message); Destroy(); }
        }

        private static Image Image(string name, Transform parent, Color color) {
            GameObject go = new GameObject(name); go.transform.SetParent(parent, false);
            Image image = go.AddComponent<Image>(); image.color = color; image.raycastTarget = false; return image;
        }
        private static Text Text(string name, Transform parent, string value, Font font, int size, Color color) {
            GameObject go = new GameObject(name); go.transform.SetParent(parent, false);
            Text text = go.AddComponent<Text>(); text.text = value; text.font = font; text.fontSize = size;
            text.fontStyle = FontStyle.Bold; text.color = color; text.alignment = TextAnchor.MiddleLeft; text.raycastTarget = false; return text;
        }
        private static void Set(RectTransform rect, Vector2 min, Vector2 max, Vector2 pivot, Vector2 position, Vector2 size) {
            rect.anchorMin = min; rect.anchorMax = max; rect.pivot = pivot; rect.anchoredPosition = position; rect.sizeDelta = size;
        }
        private static void Draw(Cell cell, Color color) {
            float width = Mathf.Max(1, cell.Graph.rect.width), height = Mathf.Max(1, cell.Graph.rect.height);
            for (int i = 0; i < cell.Lines.Length; i++) {
                float x = i * width / (Samples - 1f), y = cell.History[i] * (height - 2);
                float dx = width / (Samples - 1f), dy = (cell.History[i + 1] - cell.History[i]) * (height - 2);
                Image image = cell.Lines[i]; image.color = color;
                image.rectTransform.anchoredPosition = new Vector2(x - width / 2, y - height / 2 + 1);
                image.rectTransform.sizeDelta = new Vector2(Mathf.Sqrt(dx * dx + dy * dy), 1.6f);
                image.rectTransform.localEulerAngles = new Vector3(0, 0, Mathf.Atan2(dy, dx) * Mathf.Rad2Deg);
            }
        }
        internal static void Destroy() {
            if (_root != null) UnityEngine.Object.Destroy(_root);
            _root = _panel = null; _layout = ""; _wasVisible = false;
        }
    }
}
