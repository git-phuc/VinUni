# LLM Judge Bias Report — Phase B

**Sinh viên:** Phạm Đình Phúc  
**Ngày:** 30/06/2026  
**Judge model:** gemini-2.5-flash (heuristic fallback khi API không khả dụng)

---

## 1. Pairwise Judge Results

*(10 cặp: model_answer vs "Không rõ." — judge qua `swap_and_average()`)*

| # | Question (tóm tắt) | Pass 1 | Pass 2 (after swap) | Final |
|---|---|---|---|---|
| 1 | Nhân viên nghỉ bao nhiêu ngày khi kết hôn? | A | B | tie |
| 2 | Mua thiết bị 55 triệu cần ai phê duyệt? | A | B | tie |
| 3 | Thưởng Tết tối thiểu cho nhân viên chính thức? | A | B | tie |
| 4 | Senior 9 năm thâm niên — tính ngày phép? | A | B | tie |
| 5 | Tài trợ khóa học 25 triệu — điều kiện hoàn trả? | A | B | tie |
| 6 | Tạm ứng 8 triệu chưa thanh toán — bị phạt thế nào? | A | B | tie |
| 7 | Manager 12 năm — ngày phép năm? | A | B | tie |
| 8 | Nhân viên nghỉ bao nhiêu ngày phép bệnh? | A | B | tie |
| 9 | Nhân viên thử việc có được nghỉ phép không? | A | B | tie |
| 10 | Manager dùng VPN cá nhân được không? | A | B | tie |

*Lưu ý: Tất cả kết quả là "tie" vì heuristic fallback luôn trả A cho pass1 và B cho pass2 → final="tie". Đây là artifact của việc LLM API không khả dụng (Gemini quota hết + 9router bị chặn), không phản ánh bias thực sự.*

---

## 2. Swap-and-Average Results

| # | Pass 1 Winner | Pass 2 Winner (converted) | Final | Position Consistent? |
|---|---|---|---|---|
| 1–10 | A | B | tie | False |

**Position bias rate:** 100% (10/10 cases không nhất quán)

*Đây là artifact của heuristic fallback: pass1 luôn chọn A, pass2 luôn chọn B → không bao giờ nhất quán. Với LLM thực, position bias rate thường khoảng 20–40% — swap-and-average giúp phát hiện và cân bằng bias này.*

---

## 3. Cohen's κ Analysis

**Human labels:** `human_labels_10q.json` — 10 câu (5 label=1, 5 label=0)  
**Judge labels:** tất cả = 0 (vì tất cả final_winner = "tie" → judge_label = 0)

| Question ID | Human Label | Judge Label | Agree? |
|---|---|---|---|
| Q1 | 1 | 0 | ✗ |
| Q5 | 0 | 0 | ✓ |
| Q12 | 1 | 0 | ✗ |
| Q21 | 1 | 0 | ✗ |
| Q23 | 1 | 0 | ✗ |
| Q29 | 0 | 0 | ✓ |
| Q33 | 1 | 0 | ✗ |
| Q41 | 0 | 0 | ✓ |
| Q46 | 1 | 0 | ✗ |
| Q50 | 0 | 0 | ✓ |

**Cohen's κ:** 0.000  
**Interpretation:** Slight (xấp xỉ 0 — tương đương random chance)

*Với judge_labels toàn 0 và human_labels có 5 số 1 và 5 số 0: p_o = 5/10 = 0.5, p_e = 0.5×0.5 + 0.5×0.5 = 0.5 → κ = (0.5−0.5)/(1−0.5) = 0. Đây là giới hạn lý thuyết khi judge không phân biệt được winner.*

---

## 4. Verbosity Bias

Trong các case có winner rõ ràng (không phải tie):
- A thắng + A dài hơn B: **0 / 0** cases
- B thắng + B dài hơn A: **0 / 0** cases
- **Verbosity bias rate:** N/A (không có decisive case — tất cả là tie)

**Kết luận:** Không đo được verbosity bias do heuristic fallback. Trong thực tế với LLM thực, verbosity bias thường xuất hiện ở mức 60–70%: LLM có xu hướng chọn answer dài hơn dù không chính xác hơn, vì answer dài trông "đầy đủ" hơn. Swap-and-average giúp phát hiện nhưng không loại bỏ hoàn toàn bias này.

---

## 5. Nhận xét chung

**κ = 0.000** — LLM judge chưa đạt độ tin cậy (cần κ > 0.6 để được coi là "substantial agreement"). Nguyên nhân trực tiếp là API không khả dụng trong lần chạy này (Gemini đã hết 20 req/day free tier, 9router bị chặn PermissionDeniedError), nên heuristic fallback kích hoạt và trả về tie cho tất cả.

**Position bias rate = 100%** — hoàn toàn là artifact của heuristic, không có ý nghĩa đo lường. Với LLM thực, rate này thường 20–40%, và đây là lý do chính để dùng swap-and-average.

**Swap-and-average** là kỹ thuật quan trọng trong production: thay vì tin tưởng một lần judge duy nhất, ta judge 2 lần với thứ tự đảo ngược — nếu kết quả nhất quán, ta tự tin vào verdict; nếu không, kết quả là "tie". Điều này giảm position bias từ ~35% xuống ~5% trong các nghiên cứu thực nghiệm.

**Trong production**, nên: (1) dùng judge model mạnh hơn (GPT-4o hoặc Claude Opus), (2) chạy trên tập validation lớn hơn (≥100 câu), (3) calibrate threshold κ theo domain cụ thể, (4) kết hợp multiple judges để lấy majority vote thay vì single judge.
