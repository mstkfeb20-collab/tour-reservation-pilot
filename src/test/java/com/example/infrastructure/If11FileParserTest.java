package com.example.infrastructure;

import com.example.domain.BankTransferFile;
import com.example.domain.Money;
import com.example.transfer.If11Fixtures;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import java.nio.charset.Charset;
import java.time.LocalDate;
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
}
