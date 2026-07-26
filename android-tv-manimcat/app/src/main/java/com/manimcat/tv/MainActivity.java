package com.manimcat.tv;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.text.InputType;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.Toast;

import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import java.util.ArrayList;

public class MainActivity extends Activity {

    private static final String DEFAULT_HOST = "192.168.1.128:3000";
    private static final String PREFS_NAME = "manimcat_prefs";
    private static final String KEY_HOST  = "server_host";

    private String serverBase;

    private static final int REQ_RECORD_AUDIO = 100;

    private WebView webView;
    private SpeechRecognizer speechRecognizer;
    private Intent speechIntent;

    private static final String JS_KEY_DOWN =
        "(function(k,c){var e=new KeyboardEvent('keydown',{key:k,code:c,keyCode:k.charCodeAt(0)||13,bubbles:true,cancelable:true});document.dispatchEvent(e);if(document.activeElement&&(document.activeElement.tagName==='INPUT'||document.activeElement.isContentEditable))document.activeElement.dispatchEvent(e);})";

    private static final String JS_FOCUS_INPUT =
        "(function(){var el=document.querySelector('input[type=text],textarea,[contenteditable]');if(el){el.focus();el.scrollIntoView({block:'center'});}})";

    private static final String JS_INJECT_VOICE =
        "(function(text){var el=document.querySelector('input[type=text],textarea,[contenteditable]');if(el){el.value=text;el.focus();el.dispatchEvent(new Event('input',{bubbles:true}));var b=el.closest('form');if(b){var s=b.querySelector('button[type=submit]');if(s)s.click();else b.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));}}})";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        String host = prefs.getString(KEY_HOST, null);
        if (host == null) {
            showServerConfig(prefs);
        } else {
            serverBase = "http://" + host;
        }

        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_FULLSCREEN |
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY |
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE |
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN |
            View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
        );

        webView = new WebView(this);
        configureWebView();
        setContentView(webView,
            new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));

        if (serverBase != null) {
            webView.loadUrl(serverBase);
        }

        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
        speechRecognizer.setRecognitionListener(new VoiceListener());
        speechIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        speechIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        speechIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "zh-CN");
        speechIntent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
    }

    private void showServerConfig(SharedPreferences prefs) {
        EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_TEXT);
        input.setHint(DEFAULT_HOST);
        input.setText(DEFAULT_HOST);
        input.setTextSize(16);
        input.setPadding(32, 16, 32, 16);

        new AlertDialog.Builder(this)
            .setTitle("ManimCat 服务器地址")
            .setMessage("输入电脑的 IP:端口（例如 192.168.1.128:3000）")
            .setView(input)
            .setCancelable(false)
            .setPositiveButton("连接", (d, w) -> {
                String entered = input.getText().toString().trim();
                if (entered.isEmpty()) entered = DEFAULT_HOST;
                prefs.edit().putString(KEY_HOST, entered).apply();
                serverBase = "http://" + entered;
                webView.loadUrl(serverBase);
            })
            .show();
    }

    private void configureWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            s.setSafeBrowsingEnabled(false);
        }

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                Uri uri = req.getUrl();
                String host = uri.getHost();
                if (host != null && (host.contains("192.168") || host.contains("localhost")
                        || host.equals("127.0.0.1"))) {
                    return false;
                }
                startActivity(new Intent(Intent.ACTION_VIEW, uri));
                return true;
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {});
        webView.setFocusable(true);
        webView.setFocusableInTouchMode(true);
        webView.requestFocus();
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getAction() != KeyEvent.ACTION_DOWN) {
            return super.dispatchKeyEvent(event);
        }

        int kc = event.getKeyCode();
        String key, code;

        switch (kc) {
            case KeyEvent.KEYCODE_DPAD_UP:
                key = "ArrowUp";    code = "ArrowUp";    break;
            case KeyEvent.KEYCODE_DPAD_DOWN:
                key = "ArrowDown";  code = "ArrowDown";  break;
            case KeyEvent.KEYCODE_DPAD_LEFT:
                key = "ArrowLeft";  code = "ArrowLeft";  break;
            case KeyEvent.KEYCODE_DPAD_RIGHT:
                key = "ArrowRight"; code = "ArrowRight"; break;
            case KeyEvent.KEYCODE_DPAD_CENTER:
            case KeyEvent.KEYCODE_ENTER:
                key = "Enter";      code = "Enter";      break;
            case KeyEvent.KEYCODE_BACK:
                key = "Escape";     code = "Escape";     break;
            case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
            case KeyEvent.KEYCODE_BUTTON_Y:
                startVoiceInput();
                return true;
            case KeyEvent.KEYCODE_BUTTON_X:
            case KeyEvent.KEYCODE_MEDIA_RECORD:
                webView.evaluateJavascript(JS_FOCUS_INPUT, null);
                return true;
            default:
                return super.dispatchKeyEvent(event);
        }

        String js = JS_KEY_DOWN + "('" + key + "','" + code + "')";
        webView.evaluateJavascript(js, null);
        return true;
    }

    @Override
    public void onBackPressed() {
        String js = JS_KEY_DOWN + "('Escape','Escape')";
        webView.evaluateJavascript(js, null);
    }

    private void startVoiceInput() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.RECORD_AUDIO}, REQ_RECORD_AUDIO);
            return;
        }
        Toast.makeText(this, "正在聆听...", Toast.LENGTH_SHORT).show();
        speechRecognizer.startListening(speechIntent);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] perms, int[] results) {
        super.onRequestPermissionsResult(requestCode, perms, results);
        if (requestCode == REQ_RECORD_AUDIO && results.length > 0
                && results[0] == PackageManager.PERMISSION_GRANTED) {
            startVoiceInput();
        }
    }

    private class VoiceListener extends android.speech.RecognitionListener {
        @Override public void onReadyForSpeech(Bundle params) {}
        @Override public void onBeginningOfSpeech() {}
        @Override public void onRmsChanged(float rmsdB) {}
        @Override public void onBufferReceived(byte[] buffer) {}
        @Override public void onEndOfSpeech() {}

        @Override
        public void onResults(Bundle results) {
            ArrayList<String> matches = results.getStringArrayList(
                    SpeechRecognizer.RESULTS_RECOGNITION);
            if (matches != null && !matches.isEmpty()) {
                String text = matches.get(0);
                webView.evaluateJavascript(JS_INJECT_VOICE + "('" + escapeJs(text) + "')", null);
            } else {
                Toast.makeText(MainActivity.this, "未识别到语音", Toast.LENGTH_SHORT).show();
            }
        }

        @Override
        public void onPartialResults(Bundle partialResults) {
            ArrayList<String> matches = partialResults.getStringArrayList(
                    SpeechRecognizer.RESULTS_RECOGNITION);
            if (matches != null && !matches.isEmpty()) {
                Toast.makeText(MainActivity.this, matches.get(0), Toast.LENGTH_SHORT).show();
            }
        }

        @Override
        public void onError(int error) {
            String msg;
            switch (error) {
                case SpeechRecognizer.ERROR_AUDIO:            msg = "音频错误"; break;
                case SpeechRecognizer.ERROR_CLIENT:           msg = "客户端错误"; break;
                case SpeechRecognizer.ERROR_SERVER:           msg = "服务器错误"; break;
                case SpeechRecognizer.ERROR_NETWORK:          msg = "网络错误"; break;
                case SpeechRecognizer.ERROR_NO_MATCH:         msg = "未识别到语音"; break;
                case SpeechRecognizer.ERROR_SPEECH_TIMEOUT:   msg = "语音超时"; break;
                case SpeechRecognizer.ERROR_RECOGNIZER_BUSY:  msg = "引擎忙碌"; break;
                case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS: msg = "权限不足"; break;
                default: msg = "未知错误 " + error;
            }
            Toast.makeText(MainActivity.this, msg, Toast.LENGTH_SHORT).show();
        }

        @Override public void onEvent(int eventType, Bundle params) {}
    }

    private static String escapeJs(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("'", "\\'")
                .replace("\n", "\\n").replace("\r", "\\r");
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (speechRecognizer != null) speechRecognizer.destroy();
        if (webView != null) webView.destroy();
    }
}
