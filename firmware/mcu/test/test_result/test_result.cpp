// test/test_result/test_result.cpp
// Unit tests for mara::Result<T> type

#include "../test_runner.h"
#include "core/Result.h"

using namespace mara;

// =============================================================================
// Result<T> tests
// =============================================================================

void test_result_ok_construction() {
    Result<int> r = Result<int>::ok(42);

    TEST_ASSERT_TRUE(r.isOk());
    TEST_ASSERT_FALSE(r.isError());
    TEST_ASSERT_TRUE(static_cast<bool>(r));
    TEST_ASSERT_EQUAL(42, r.value());
    TEST_ASSERT_EQUAL(ErrorCode::Ok, r.errorCode());
}

void test_result_error_construction() {
    Result<int> r = Result<int>::err(ErrorCode::InvalidArgument);

    TEST_ASSERT_FALSE(r.isOk());
    TEST_ASSERT_TRUE(r.isError());
    TEST_ASSERT_FALSE(static_cast<bool>(r));
    TEST_ASSERT_EQUAL(ErrorCode::InvalidArgument, r.errorCode());
}

void test_result_value_or() {
    Result<int> ok = Result<int>::ok(42);
    Result<int> err = Result<int>::err(ErrorCode::NotFound);

    TEST_ASSERT_EQUAL(42, ok.valueOr(99));
    TEST_ASSERT_EQUAL(99, err.valueOr(99));
}

void test_result_move_value() {
    Result<int> r = Result<int>::ok(100);
    int val = static_cast<Result<int>&&>(r).value();
    TEST_ASSERT_EQUAL(100, val);
}

// =============================================================================
// Result<void> tests
// =============================================================================

void test_void_result_ok() {
    Result<void> r = Result<void>::ok();

    TEST_ASSERT_TRUE(r.isOk());
    TEST_ASSERT_FALSE(r.isError());
    TEST_ASSERT_TRUE(static_cast<bool>(r));
    TEST_ASSERT_EQUAL(ErrorCode::Ok, r.errorCode());
}

void test_void_result_error() {
    Result<void> r = Result<void>::err(ErrorCode::Timeout);

    TEST_ASSERT_FALSE(r.isOk());
    TEST_ASSERT_TRUE(r.isError());
    TEST_ASSERT_FALSE(static_cast<bool>(r));
    TEST_ASSERT_EQUAL(ErrorCode::Timeout, r.errorCode());
}

// =============================================================================
// ErrorCode string mapping tests
// =============================================================================

void test_error_code_to_string() {
    TEST_ASSERT_EQUAL_STRING("Ok", errorCodeToString(ErrorCode::Ok));
    TEST_ASSERT_EQUAL_STRING("InvalidArgument", errorCodeToString(ErrorCode::InvalidArgument));
    TEST_ASSERT_EQUAL_STRING("Timeout", errorCodeToString(ErrorCode::Timeout));
    TEST_ASSERT_EQUAL_STRING("MotorNotAttached", errorCodeToString(ErrorCode::MotorNotAttached));
    TEST_ASSERT_EQUAL_STRING("SafetyEstopped", errorCodeToString(ErrorCode::SafetyEstopped));
}

// =============================================================================
// TRY macro tests
// =============================================================================

Result<void> helper_ok() {
    return Result<void>::ok();
}

Result<void> helper_err() {
    return Result<void>::err(ErrorCode::NotInitialized);
}

Result<void> test_try_propagates_ok() {
    TRY(helper_ok());
    return Result<void>::ok();
}

Result<void> test_try_propagates_error() {
    TRY(helper_err());  // Should return early
    return Result<void>::ok();  // Never reached
}

void test_try_macro_ok_path() {
    Result<void> r = test_try_propagates_ok();
    TEST_ASSERT_TRUE(r.isOk());
}

void test_try_macro_error_path() {
    Result<void> r = test_try_propagates_error();
    TEST_ASSERT_TRUE(r.isError());
    TEST_ASSERT_EQUAL(ErrorCode::NotInitialized, r.errorCode());
}

// =============================================================================
// Different value types
// =============================================================================

void test_result_with_float() {
    Result<float> r = Result<float>::ok(3.14f);
    TEST_ASSERT_TRUE(r.isOk());
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 3.14f, r.value());
}

void test_result_with_pointer() {
    int x = 42;
    Result<int*> r = Result<int*>::ok(&x);
    TEST_ASSERT_TRUE(r.isOk());
    TEST_ASSERT_EQUAL_PTR(&x, r.value());
    TEST_ASSERT_EQUAL(42, *r.value());
}

void test_result_with_struct() {
    struct Point { int x; int y; };
    Point p{10, 20};
    Result<Point> r = Result<Point>::ok(p);
    TEST_ASSERT_TRUE(r.isOk());
    TEST_ASSERT_EQUAL(10, r.value().x);
    TEST_ASSERT_EQUAL(20, r.value().y);
}

// =============================================================================
// Test runner
// =============================================================================

void run_tests() {
    // Result<T> tests
    RUN_TEST(test_result_ok_construction);
    RUN_TEST(test_result_error_construction);
    RUN_TEST(test_result_value_or);
    RUN_TEST(test_result_move_value);

    // Result<void> tests
    RUN_TEST(test_void_result_ok);
    RUN_TEST(test_void_result_error);

    // ErrorCode string mapping
    RUN_TEST(test_error_code_to_string);

    // TRY macro
    RUN_TEST(test_try_macro_ok_path);
    RUN_TEST(test_try_macro_error_path);

    // Different value types
    RUN_TEST(test_result_with_float);
    RUN_TEST(test_result_with_pointer);
    RUN_TEST(test_result_with_struct);
}

TEST_RUNNER(run_tests)
