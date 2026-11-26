package com.example.infrastructure;

import com.example.domain.BankTransferFile;
import com.example.domain.Money;
import com.example.transfer.If11Fixtures;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import java.nio.charset.Charset;
import java.time.LocalDate;
import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

@Tag("REQ-24001")
@DisplayName("REQ-24001 IF-11振込入金通知ファイル")
class If11FileParserTest {

    private final If11FileParser parser = new If11FileParser();

    @Test
    @DisplayName("有効な固定長ファイルを読み取り、データ0件も受け付ける")
    void parsesDetailsAndEmptyFile() {
        BankTransferFile file = parser.parse(If11Fixtures.file(List.of(
            new If11Fixtures.Detail("000001", 12_345, "R000000000001", "0", "R000000000001")
        )));
        BankTransferFile emptyFile = parser.parse(If11Fixtures.file(List.of()));

        assertEquals(LocalDate.of(2026, 4, 1), file.creationDate());
        assertEquals("1234567", file.accountNumber());
        assertEquals(1, file.details().size());
        assertEquals("000001", file.details().get(0).inquiryNo());
        assertEquals(Money.yen(12_345), file.details().get(0).amount());
        assertEquals("R000000000001", file.details().get(0).payerName().trim());
        assertEquals(Money.yen(12_345), file.totalAmount());
        assertEquals(0, emptyFile.details().size());
        assertEquals(Money.zero(), emptyFile.totalAmount());
    }

    @Test
    @DisplayName("トレーラーの件数・金額の不一致は形式エラーにする")
    void rejectsTrailerMismatch() {
        byte[] file = If11Fixtures.file(List.of(
            new If11Fixtures.Detail("000001", 12_345, "R000000000001", "0", "")
        ));
        file[411] = '9';

        assertThrows(IllegalArgumentException.class, () -> parser.parse(file));
    }

    @Test
    @DisplayName("数値以外の金額と200バイトでないレコードは形式エラーにする")
    void rejectsMalformedFieldsAndLengths() {
        byte[] invalidAmount = If11Fixtures.file(List.of(
            new If11Fixtures.Detail("000001", 12_345, "R000000000001", "0", "")
        ));
        invalidAmount[221] = 'X';
        byte[] invalidLength = If11Fixtures.file(List.of());
        byte[] shortened = new byte[invalidLength.length - 1];
        System.arraycopy(invalidLength, 0, shortened, 0, 100);
        System.arraycopy(invalidLength, 101, shortened, 100, invalidLength.length - 101);

        assertThrows(IllegalArgumentException.class, () -> parser.parse(invalidAmount));
        assertThrows(IllegalArgumentException.class, () -> parser.parse(shortened));
    }

    @Test
    @DisplayName("CRLF以外のレコード区切りと異なる入金口座は受け付けない")
    void rejectsWrongLineEndingAndAccount() {
        byte[] lfFile = If11Fixtures.file(List.of());
        lfFile[200] = '\n';
        byte[] wrongAccount = If11Fixtures.file(List.of());
        byte[] account = "7654321".getBytes(Charset.forName("Shift_JIS"));
        System.arraycopy(account, 0, wrongAccount, 7, account.length);
        byte[] invalidDate = If11Fixtures.file(List.of());
        invalidDate[5] = '3';
        invalidDate[6] = '2';

        assertThrows(IllegalArgumentException.class, () -> parser.parse(lfFile));
        assertThrows(IllegalArgumentException.class, () -> parser.parse(wrongAccount));
        assertThrows(IllegalArgumentException.class, () -> parser.parse(invalidDate));
    }

    @Test
    @DisplayName("IF-11で未定義のヘッダー・トレーラー領域を空白と決めつけない")
    void acceptsUnspecifiedHeaderAndTrailerFields() {
        byte[] file = If11Fixtures.file(List.of());
        file[14] = 'A';
        file[202 + 19] = 'B';

        assertEquals(0, parser.parse(file).details().size());
    }

    @Test
    @DisplayName("レコードの不足や区分の順序違いを形式エラーにする")
    void rejectsMissingOrMisorderedRecords() {
        byte[] empty = If11Fixtures.file(List.of());
        byte[] tooFew = Arrays.copyOf(empty, 2 * 202);
        assertEquals("ヘッダー・トレーラー・エンドが必要です",
            assertThrows(IllegalArgumentException.class, () -> parser.parse(tooFew)).getMessage());

        for (int offset : new int[] {0, 202, 404}) {
            byte[] wrongType = empty.clone();
            wrongType[offset] = '2';
            assertEquals("レコード区分の順序または値が正しくありません",
                assertThrows(IllegalArgumentException.class, () -> parser.parse(wrongType)).getMessage());
        }
        byte[] detail = oneDetail();
        detail[202] = '1';
        assertEquals("レコード区分の順序または値が正しくありません",
            assertThrows(IllegalArgumentException.class, () -> parser.parse(detail)).getMessage());
    }

    @Test
    @DisplayName("同一勘定日の照会番号の重複と不正な取消区分を拒否する")
    void rejectsDuplicateInquiryAndInvalidCancellationCode() {
        If11Fixtures.Detail detail = new If11Fixtures.Detail("000001", 100, "R000000000001", "0", "");
        byte[] duplicate = If11Fixtures.file(List.of(detail, detail));
        assertEquals("照会番号が重複しています: 000001",
            assertThrows(IllegalArgumentException.class, () -> parser.parse(duplicate)).getMessage());

        byte[] invalidCode = oneDetail();
        invalidCode[202 + 127] = '2';
        assertEquals("取消区分は0または1で指定してください",
            assertThrows(IllegalArgumentException.class, () -> parser.parse(invalidCode)).getMessage());

        byte[] reversal = oneDetail();
        reversal[202 + 127] = '1';
        assertEquals("1", parser.parse(reversal).details().get(0).cancellationCode());
    }

    @Test
    @DisplayName("照会番号と他店券金額と振込依頼人コードは数字で指定する")
    void rejectsNonNumericDetailFields() {
        int[] offsets = {1, 29, 39};
        String[] messages = {"照会番号は数字で指定してください", "他店券金額は数字で指定してください",
            "振込依頼人コードは数字で指定してください"};
        for (int i = 0; i < offsets.length; i++) {
            byte[] file = oneDetail();
            file[202 + offsets[i]] = 'A';
            assertEquals(messages[i], assertThrows(IllegalArgumentException.class, () -> parser.parse(file)).getMessage());
        }
    }

    @Test
    @DisplayName("データとエンドの未使用領域には空白を指定する")
    void rejectsNonSpacePadding() {
        byte[] detailPadding = oneDetail();
        detailPadding[202 + 148] = 'A';
        byte[] endPadding = oneDetail();
        endPadding[606 + 1] = 'A';
        for (byte[] file : List.of(detailPadding, endPadding)) {
            assertEquals("未使用領域は空白で指定してください",
                assertThrows(IllegalArgumentException.class, () -> parser.parse(file)).getMessage());
        }
    }

    @Test
    @DisplayName("半角英数字と半角カナを受け付け、その他の文字を拒否する")
    void validatesCharacterEncoding() {
        byte[] valid = If11Fixtures.file(List.of(
            new If11Fixtures.Detail("000001", 100, "aZ09ｱ", "0", "")
        ));
        assertEquals("aZ09ｱ", parser.parse(valid).details().get(0).payerName().trim());

        byte[] punctuation = oneDetail();
        punctuation[202 + 49] = '!';
        assertEquals("半角英数字と半角カナ以外の文字が含まれています",
            assertThrows(IllegalArgumentException.class, () -> parser.parse(punctuation)).getMessage());

        byte[] malformed = oneDetail();
        malformed[202 + 49] = (byte) 0x81;
        malformed[202 + 50] = ' ';
        assertEquals("Shift_JISとして読めない文字が含まれています",
            assertThrows(IllegalArgumentException.class, () -> parser.parse(malformed)).getMessage());
    }

    private byte[] oneDetail() {
        return If11Fixtures.file(List.of(new If11Fixtures.Detail("000001", 100, "R000000000001", "0", "")));
    }
}
