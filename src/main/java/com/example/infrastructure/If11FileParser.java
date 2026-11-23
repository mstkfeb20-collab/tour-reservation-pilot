package com.example.infrastructure;

import com.example.domain.BankTransferDetail;
import com.example.domain.BankTransferFile;
import com.example.domain.Money;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.Charset;
import java.nio.charset.CodingErrorAction;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class If11FileParser {

    private static final Charset SHIFT_JIS = Charset.forName("Shift_JIS");
    private static final int RECORD_LENGTH = 200;

    public BankTransferFile parse(byte[] fileContent) {
        List<byte[]> records = splitRecords(fileContent);
        if (records.size() < 3) {
            throw formatError("ヘッダー・トレーラー・エンドが必要です");
        }

        for (byte[] record : records) {
            if (record.length != RECORD_LENGTH) {
                throw formatError("レコードは200バイトで指定してください");
            }
            validateEncoding(record);
        }

        byte[] header = records.get(0);
        requireType(header, '1');
        LocalDate creationDate = date(header, 1, 7, "作成日");
        String accountNumber = text(header, 7, 14);
        if (!accountNumber.equals("1234567")) {
            throw formatError("入金口座番号が1234567ではありません");
        }
        requireSpaces(header, 14, RECORD_LENGTH);

        byte[] trailer = records.get(records.size() - 2);
        byte[] end = records.get(records.size() - 1);
        requireType(trailer, '8');
        requireType(end, '9');
        requireSpaces(end, 1, RECORD_LENGTH);
        int trailerCount = integer(trailer, 1, 7, "合計件数");
        long trailerAmount = number(trailer, 7, 19, "合計金額");
        requireSpaces(trailer, 19, RECORD_LENGTH);

        List<BankTransferDetail> details = new ArrayList<>();
        Set<String> inquiryNumbers = new HashSet<>();
        Money totalAmount = Money.zero();
        for (int i = 1; i < records.size() - 2; i++) {
            byte[] record = records.get(i);
            requireType(record, '2');
            String inquiryNo = text(record, 1, 7);
            requireDigits(inquiryNo, "照会番号");
            LocalDate accountDate = date(record, 7, 13, "勘定日");
            if (!inquiryNumbers.add(accountDate + ":" + inquiryNo)) {
                throw formatError("照会番号が重複しています: " + inquiryNo);
            }
            LocalDate startDate = date(record, 13, 19, "起算日");
            Money amount = Money.yen(number(record, 19, 29, "金額"));
            digits(record, 29, 39, "他店券金額");
            digits(record, 39, 49, "振込依頼人コード");
            String payerName = text(record, 49, 97);
            text(record, 97, 112);
            text(record, 112, 127);
            String cancellationCode = text(record, 127, 128);
            if (!cancellationCode.equals("0") && !cancellationCode.equals("1")) {
                throw formatError("取消区分は0または1で指定してください");
            }
            String ediInformation = text(record, 128, 148);
            requireSpaces(record, 148, RECORD_LENGTH);
            details.add(new BankTransferDetail(inquiryNo, accountDate, startDate, amount, payerName, cancellationCode, ediInformation));
            totalAmount = totalAmount.plus(amount);
        }

        if (trailerCount != details.size() || trailerAmount != totalAmount.toLong()) {
            throw formatError("トレーラーの合計件数または合計金額が明細と一致しません");
        }
        return new BankTransferFile(creationDate, accountNumber, details, totalAmount);
    }

    private List<byte[]> splitRecords(byte[] content) {
        List<byte[]> records = new ArrayList<>();
        int recordStart = 0;
        for (int i = 0; i < content.length; i++) {
            if (content[i] == '\n') {
                throw formatError("レコードの区切りはCRLFで指定してください");
            }
            if (content[i] == '\r') {
                if (i + 1 >= content.length || content[i + 1] != '\n') {
                    throw formatError("レコードの区切りはCRLFで指定してください");
                }
                records.add(Arrays.copyOfRange(content, recordStart, i));
                recordStart = i + 2;
                i++;
            }
        }
        if (recordStart != content.length || records.isEmpty()) {
            throw formatError("ファイルはCRLFで終端してください");
        }
        return records;
    }

    private void validateEncoding(byte[] record) {
        try {
            String decoded = SHIFT_JIS.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(ByteBuffer.wrap(record))
                .toString();
            if (decoded.length() != RECORD_LENGTH || decoded.chars().anyMatch(c -> !isAllowedCharacter(c))) {
                throw formatError("半角英数字と半角カナ以外の文字が含まれています");
            }
        } catch (CharacterCodingException exception) {
            throw formatError("Shift_JISとして読めない文字が含まれています");
        }
    }

    private LocalDate date(byte[] record, int start, int end, String label) {
        String value = text(record, start, end);
        requireDigits(value, label);
        try {
            return LocalDate.of(
                2000 + Integer.parseInt(value.substring(0, 2)),
                Integer.parseInt(value.substring(2, 4)),
                Integer.parseInt(value.substring(4, 6))
            );
        } catch (java.time.DateTimeException exception) {
            throw formatError(label + "が正しい日付ではありません");
        }
    }

    private int integer(byte[] record, int start, int end, String label) {
        return Math.toIntExact(number(record, start, end, label));
    }

    private long number(byte[] record, int start, int end, String label) {
        String value = text(record, start, end);
        requireDigits(value, label);
        try {
            return Long.parseLong(value);
        } catch (NumberFormatException exception) {
            throw formatError(label + "が数値の範囲を超えています");
        }
    }

    private void digits(byte[] record, int start, int end, String label) {
        requireDigits(text(record, start, end), label);
    }

    private void requireDigits(String value, String label) {
        if (!value.matches("[0-9]+")) {
            throw formatError(label + "は数字で指定してください");
        }
    }

    private String text(byte[] record, int start, int end) {
        return new String(record, start, end - start, SHIFT_JIS);
    }

    private void requireType(byte[] record, char type) {
        if (record[0] != (byte) type) {
            throw formatError("レコード区分の順序または値が正しくありません");
        }
    }

    private void requireSpaces(byte[] record, int start, int end) {
        for (int i = start; i < end; i++) {
            if (record[i] != ' ') {
                throw formatError("未使用領域は空白で指定してください");
            }
        }
    }

    private boolean isAllowedCharacter(int character) {
        return character == ' '
            || character >= '0' && character <= '9'
            || character >= 'A' && character <= 'Z'
            || character >= 'a' && character <= 'z'
            || character >= 0xff61 && character <= 0xff9f;
    }

    private IllegalArgumentException formatError(String message) {
        return new IllegalArgumentException(message);
    }
}
