<template>
  <div v-if="!$fetchState.pending && !$fetchState.error" class="wrapper">
    <template v-if="!!record">
      <RecordFeedbackTaskComponent
        :recordStatus="record.status"
        :fields="record.fields"
      />

      <QuestionsFormComponent
        :key="record.id"
        class="question-form"
        :class="statusClass"
        :datasetId="datasetId"
        :record="record"
        @on-submit-responses="goToNext"
        @on-discard-responses="goToNext"
        @on-question-form-touched="onQuestionFormTouched"
      />
    </template>

    <div v-else class="wrapper--empty">
      <p
        v-if="!records.hasRecordsToAnnotate"
        class="wrapper__text --heading3"
        v-text="noRecordsMessage"
      />
      <BaseSpinner v-else />
    </div>
  </div>
</template>

<script>
import { isNil } from "lodash";
import { Notification } from "@/models/Notifications";
import { RECORD_STATUS } from "@/models/feedback-task-model/record/record.queries";
import { useRecordFeedbackTaskViewModel } from "./useRecordFeedbackTaskViewModel";

export default {
  name: "RecordFeedbackTaskAndQuestionnaireComponent",
  props: {
    datasetId: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      questionFormTouched: false,
      recordStatusToFilterWith: null,
      searchTextToFilterWith: null,
      currentPage: null,
      fetching: false,
    };
  },
  computed: {
    noMoreDataMessage() {
      return `You've reached the end of the data for the ${this.recordStatusToFilterWith} queue.`;
    },
    record() {
      return this.records.getRecordOn(this.currentPage);
    },
    noRecordsMessage() {
      if (
        isNil(this.searchTextToFilterWith) ||
        this.searchTextToFilterWith.length === 0
      )
        return `You have no ${this.recordStatusToFilterWith} records`;
      return `You have no ${this.recordStatusToFilterWith} records matching the search input`;
    },
    statusClass() {
      return `--${this.record.status}`;
    },
    statusFilterFromQuery() {
      return this.$route.query?._status ?? RECORD_STATUS.PENDING.toLowerCase();
    },
    searchFilterFromQuery() {
      return this.$route.query?._search ?? "";
    },
    pageFromQuery() {
      const { _page } = this.$route.query;
      return isNil(_page) ? 1 : +_page;
    },
  },
  async fetch() {
    if (this.fetching) return Promise.resolve();

    this.fetching = true;
    this.clearRecords();

    await this.loadRecords(
      this.datasetId,
      this.currentPage,
      this.recordStatusToFilterWith,
      this.searchTextToFilterWith
    );

    const isRecordExistForCurrentPage = this.records.existsRecordOn(
      this.currentPage
    );

    if (!isRecordExistForCurrentPage && this.currentPage !== 1) {
      this.currentPage = 1;

      await this.loadRecords(
        this.datasetId,
        this.currentPage,
        this.recordStatusToFilterWith,
        this.searchTextToFilterWith
      );
    }

    this.fetching = false;
  },
  watch: {
    async currentPage(newValue) {
      // TODO - regroup in a common watcher hover filterParams computed
      await this.$router.push({
        path: this.$route.path,
        query: {
          ...this.$route.query,
          _page: newValue,
          _status: this.recordStatusToFilterWith,
        },
      });
    },
    async recordStatusToFilterWith(newValue) {
      // TODO - regroup in a common watcher hover filterParams computed
      await this.$router.push({
        path: this.$route.path,
        query: {
          ...this.$route.query,
          _status: newValue,
          _search: this.searchTextToFilterWith,
          _page: this.currentPage,
        },
      });
    },
    async searchTextToFilterWith(newValue) {
      // TODO - regroup in a common watcher hover filterParams computed
      await this.$router.push({
        path: this.$route.path,
        query: {
          ...this.$route.query,
          _search: newValue,
          _status: this.recordStatusToFilterWith,
          _page: this.currentPage,
        },
      });
    },
  },
  created() {
    this.recordStatusToFilterWith = this.statusFilterFromQuery;
    this.searchTextToFilterWith = this.searchFilterFromQuery;
    this.currentPage = this.pageFromQuery;

    this.loadMetrics(this.datasetId);
  },
  mounted() {
    this.$root.$on("go-to-next-page", () => {
      this.setCurrentPage(this.currentPage + 1);
    });
    this.$root.$on("go-to-prev-page", () => {
      this.setCurrentPage(this.currentPage - 1);
    });
    this.$root.$on("status-filter-changed", this.onStatusFilterChanged);
    this.$root.$on("search-filter-changed", this.onSearchFilterChanged);
  },
  methods: {
    async applyStatusFilter(status) {
      this.currentPage = 1;
      this.recordStatusToFilterWith = status;

      await this.$fetch();

      this.checkAndEmitTotalRecords({
        searchFilter: this.searchTextToFilterWith,
        value: this.records.total,
      });
    },
    async applySearchFilter(searchFilter) {
      this.currentPage = 1;
      this.searchTextToFilterWith = searchFilter;

      await this.$fetch();

      this.checkAndEmitTotalRecords({
        searchFilter,
        value: this.records.total,
      });
    },
    emitResetStatusFilter() {
      this.$root.$emit("reset-status-filter");
    },
    emitResetSearchFilter() {
      this.$root.$emit("reset-search-filter");
    },
    checkAndEmitTotalRecords({ searchFilter, value }) {
      if (searchFilter?.length) {
        this.$root.$emit("total-records", value);
      } else {
        this.$root.$emit("total-records", null);
      }
    },
    async onSearchFilterChanged(newSearchValue) {
      const localApplySearchFilter = this.applySearchFilter;
      const localEmitResetSearchFilter = this.emitResetSearchFilter;

      if (
        this.questionFormTouched &&
        newSearchValue !== this.searchFilterFromQuery
      ) {
        return Notification.dispatch("notify", {
          message: this.$t("changes_no_submit"),
          buttonText: this.$t("button.ignore_and_continue"),
          numberOfChars: 500,
          type: "warning",
          async onClick() {
            await localApplySearchFilter(newSearchValue);
          },
          onClose() {
            localEmitResetSearchFilter();
          },
        });
      }

      if (newSearchValue !== this.searchFilterFromQuery)
        return await this.applySearchFilter(newSearchValue);
    },
    async onStatusFilterChanged(newStatus) {
      if (this.recordStatusToFilterWith === newStatus) {
        return;
      }

      const localApplyStatusFilter = this.applyStatusFilter;
      const localEmitResetStatusFilter = this.emitResetStatusFilter;

      if (this.questionFormTouched) {
        Notification.dispatch("notify", {
          message: this.$t("changes_no_submit"),
          buttonText: this.$t("button.ignore_and_continue"),
          numberOfChars: 500,
          type: "warning",
          async onClick() {
            await localApplyStatusFilter(newStatus);
          },
          onClose() {
            localEmitResetStatusFilter();
          },
        });
      } else {
        await this.applyStatusFilter(newStatus);
      }
    },
    onQuestionFormTouched(isTouched) {
      this.questionFormTouched = isTouched;
    },
    async setCurrentPage(newPage) {
      if (this.fetching) return Promise.resolve();

      this.fetching = true;

      let isNextRecordExist = this.records.existsRecordOn(newPage);

      if (!isNextRecordExist) {
        await this.loadRecords(
          this.datasetId,
          newPage,
          this.recordStatusToFilterWith,
          this.searchTextToFilterWith
        );

        isNextRecordExist = this.records.existsRecordOn(newPage);
      }

      if (isNextRecordExist) {
        this.currentPage = newPage;
      } else if (this.currentPage < newPage) {
        Notification.dispatch("notify", {
          message: this.noMoreDataMessage,
          numberOfChars: this.noMoreDataMessage.length,
          type: "info",
        });
      }

      this.fetching = false;
    },
    goToNext() {
      this.setCurrentPage(this.currentPage + 1);
    },
  },
  beforeDestroy() {
    this.$root.$off("go-to-next-page");
    this.$root.$off("go-to-prev-page");
    this.$root.$off("status-filter-changed");
    this.$root.$off("search-filter-changed");
    Notification.dispatch("clear");
  },
  setup() {
    return useRecordFeedbackTaskViewModel();
  },
};
</script>

<style lang="scss" scoped>
.wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: $base-space * 2;
  height: 100%;
  &__text {
    color: $black-54;
  }
  &--empty {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}
.question-form {
  border: 1px solid transparent;
  background: palette(white);
  &.--pending {
    border-color: transparent;
  }
  &.--discarded {
    border-color: #c3c3c3;
  }
  &.--submitted {
    border-color: $primary-color;
  }
}
</style>
