package com.aws.cfn.scheduler;

import org.junit.Test;

import java.time.Clock;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.core.Is.is;
import static org.hamcrest.core.IsEqual.equalTo;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

public class CronHelperTest {

    @Test
    public void testGenerateOneTimeCronExpression_Simple() {

        final DateTimeFormatter f = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
        final LocalDateTime dateTime = LocalDateTime.parse("2018-10-30 13:40:23", f);
        final Clock mockClockInASock = mock(Clock.class);
        when(mockClockInASock.instant()).thenReturn(dateTime.toInstant(ZoneOffset.UTC));

        final CronHelper cronHelper = new CronHelper(mockClockInASock);

        assertThat(
            cronHelper.generateOneTimeCronExpression(5),
            is(equalTo("cron(45 13 30 10 ? 2018)"))
        );
    }

    @Test
    public void testGenerateOneTimeCronExpression_DayBreak() {

        final DateTimeFormatter f = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
        final LocalDateTime dateTime = LocalDateTime.parse("2018-10-30 23:59:01", f);
        final Clock mockClockInASock = mock(Clock.class);
        when(mockClockInASock.instant()).thenReturn(dateTime.toInstant(ZoneOffset.UTC));

        final CronHelper cronHelper = new CronHelper(mockClockInASock);

        assertThat(
            cronHelper.generateOneTimeCronExpression(3),
            is(equalTo("cron(2 0 31 10 ? 2018)"))
        );
    }

    @Test
    public void testGenerateOneTimeCronExpression_YearBreak() {

        final DateTimeFormatter f = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
        final LocalDateTime dateTime = LocalDateTime.parse("2018-12-31 23:56:59", f);
        final Clock mockClockInASock = mock(Clock.class);
        when(mockClockInASock.instant()).thenReturn(dateTime.toInstant(ZoneOffset.UTC));

        final CronHelper cronHelper = new CronHelper(mockClockInASock);

        assertThat(
            cronHelper.generateOneTimeCronExpression(5),
            is(equalTo("cron(1 0 1 1 ? 2019)"))
        );
    }
}

