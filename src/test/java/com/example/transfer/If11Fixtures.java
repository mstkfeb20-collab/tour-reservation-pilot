package com.example.transfer;

import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.List;

public final class If11Fixtures {

    private static final Charset SHIFT_JIS = Charset.forName("Shift_JIS");

    private If11Fixtures() {
    }

    public static byte[] file(List<Detail> details) {
        List<String> records = new ArrayList<>();
        records.add(record('1', 1, "260401"));
        long total = 0;
        for (Detail detail : details) {
            records.add(dataRecord(detail));
            total += detail.amount();
        }
        records.add(record('8', 1, String.format("%06d", details.size()) + String.format("%012d", total)));
        records.add(record('9', 1, ""));
        return (String.join("\r\n", records) + "\r\n").getBytes(SHIFT_JIS);
    }

    public static String dataRecord(Detail detail) {
        char[] chars = blankRecord('2');
        put(chars, 1, detail.inquiryNo());
        put(chars, 7, "260401");
        put(chars, 13, "260401");
        put(chars, 19, String.format("%010d", detail.amount()));
        put(chars, 29, "0000000000");
        put(chars, 39, "0000000000");
        put(chars, 49, String.format("%-48s", detail.payerName()));
        put(chars, 97, String.format("%-15s", "ﾐﾂｲ"));
        put(chars, 112, String.format("%-15s", "ﾄｳｷｮｳ"));
        put(chars, 127, detail.cancellationCode());
        put(chars, 128, String.format("%-20s", detail.ediInformation()));
        return new String(chars);
    }

    private static String record(char type, int start, String value) {
        char[] chars = blankRecord(type);
        put(chars, start, value);
        if (type == '1') {
            put(chars, 7, "1234567");
        }
        return new String(chars);
    }

    private static char[] blankRecord(char type) {
        char[] chars = new char[200];
        java.util.Arrays.fill(chars, ' ');
        chars[0] = type;
        return chars;
    }

    private static void put(char[] chars, int start, String value) {
        value.getChars(0, value.length(), chars, start);
    }

    public record Detail(String inquiryNo, long amount, String payerName, String cancellationCode, String ediInformation) {
    }
}
