package com.example.domain;

import java.time.LocalDate;
import java.util.Objects;

/**
 * 予約。振込状況は 未振込 → 振込済 → 取消、または 未振込 → 取消 の順にしか進まない。
 * 取消は終端で、他の状態に戻らない（INV-002）。
 */
public final class Reservation {

    public static final int REMARKS_MAX_LENGTH = 80;

    private final String reserveNo;
    private final String tourCode;
    private final int adultCount;
    private final int childCount;
    private final Money sumPrice;
    private final String remarks;
    private final LocalDate payDueDate;
    private TransferStatus status;
    private LocalDate paidDate;
    private Money paidAmount;
    private boolean latePayment;
    private long version = 1;

    private Reservation(String reserveNo, String tourCode, int adultCount, int childCount, Money sumPrice, String remarks, LocalDate payDueDate) {
        this.reserveNo = Objects.requireNonNull(reserveNo);
        this.tourCode = Objects.requireNonNull(tourCode);
        this.adultCount = adultCount;
        this.childCount = childCount;
        this.sumPrice = Objects.requireNonNull(sumPrice);
        this.remarks = remarks == null ? "" : remarks;
        this.payDueDate = payDueDate;
        this.status = TransferStatus.UNPAID;
    }

    /** 入力条件（REQ-001）を満たす予約だけを作る。 */
    public static Reservation create(String reserveNo, Tour tour, int adultCount, int childCount, String remarks) {
        return create(reserveNo, tour, adultCount, childCount, remarks, null);
    }

    public static Reservation create(String reserveNo, Tour tour, int adultCount, int childCount, String remarks, LocalDate payDueDate) {
        if (adultCount < 0 || childCount < 0) {
            throw new IllegalArgumentException("人数は0以上で指定してください");
        }
        if (adultCount + childCount == 0) {
            throw new IllegalArgumentException("人数を入力してください");
        }
        if (adultCount == 0) {
            throw new IllegalArgumentException("お子様のみのご予約はお受けできません");
        }
        if (remarks != null && remarks.length() > REMARKS_MAX_LENGTH) {
            throw new IllegalArgumentException("備考は" + REMARKS_MAX_LENGTH + "文字以内で入力してください");
        }
        return new Reservation(reserveNo, tour.code(), adultCount, childCount, tour.priceFor(adultCount, childCount), remarks, payDueDate);
    }

    public synchronized void markPaid() {
        if (status != TransferStatus.UNPAID) {
            throw new IllegalStateException("予約 " + reserveNo + " は" + status.label() + "のため振込済にできません");
        }
        status = TransferStatus.PAID;
        version++;
    }

    public synchronized void markPaid(long expectedVersion, LocalDate date, Money amount, boolean latePayment) {
        if (version != expectedVersion) {
            throw new IllegalStateException("予約 " + reserveNo + " は他の処理で更新されています");
        }
        if (status != TransferStatus.UNPAID) {
            throw new IllegalStateException("予約 " + reserveNo + " は" + status.label() + "のため振込済にできません");
        }
        paidDate = Objects.requireNonNull(date);
        paidAmount = Objects.requireNonNull(amount);
        this.latePayment = latePayment;
        status = TransferStatus.PAID;
        version++;
    }

    public synchronized void cancel() {
        if (status == TransferStatus.CANCELLED) {
            throw new IllegalStateException("予約 " + reserveNo + " は取り消し済みです");
        }
        status = TransferStatus.CANCELLED;
        version++;
    }

    public int headcount() {
        return adultCount + childCount;
    }

    public String reserveNo() {
        return reserveNo;
    }

    public String tourCode() {
        return tourCode;
    }

    public Money sumPrice() {
        return sumPrice;
    }

    public String remarks() {
        return remarks;
    }

    public synchronized TransferStatus status() {
        return status;
    }

    public LocalDate payDueDate() {
        return payDueDate;
    }

    public synchronized LocalDate paidDate() {
        return paidDate;
    }

    public synchronized Money paidAmount() {
        return paidAmount;
    }

    public synchronized boolean latePayment() {
        return latePayment;
    }

    public synchronized long version() {
        return version;
    }
}
