#include "nativeweave_api_v1.h"
#include <stdio.h>
#if defined(__cplusplus)
#define NW_ASSERT static_assert
#else
#define NW_ASSERT _Static_assert
#endif
NW_ASSERT(sizeof(void *) == 8, "This probe certifies only the x64 initial profile");
NW_ASSERT(sizeof(nw_status) == 4, "status");
NW_ASSERT(sizeof(nw_abi_info_v1) == 32, "abi info");
NW_ASSERT(offsetof(nw_abi_info_v1, struct_size) == 0, "abi size");
NW_ASSERT(offsetof(nw_abi_info_v1, abi_major) == 4, "abi major");
NW_ASSERT(offsetof(nw_abi_info_v1, abi_minor) == 8, "abi minor");
NW_ASSERT(offsetof(nw_abi_info_v1, pointer_width_bits) == 12, "abi pointer width");
NW_ASSERT(offsetof(nw_abi_info_v1, capabilities) == 16, "abi caps");
NW_ASSERT(offsetof(nw_abi_info_v1, reserved) == 24, "abi reserved");
NW_ASSERT(sizeof(nw_error_info_v1) == 24, "error");
NW_ASSERT(offsetof(nw_error_info_v1, struct_size) == 0, "error size");
NW_ASSERT(offsetof(nw_error_info_v1, domain) == 4, "error domain");
NW_ASSERT(offsetof(nw_error_info_v1, code) == 8, "error code");
NW_ASSERT(offsetof(nw_error_info_v1, flags) == 12, "error flags");
NW_ASSERT(offsetof(nw_error_info_v1, correlation_id) == 16, "error correlation");
NW_ASSERT(sizeof(nw_bytes_view_v1) == 16, "bytes");
NW_ASSERT(offsetof(nw_bytes_view_v1, data) == 0, "bytes pointer");
NW_ASSERT(offsetof(nw_bytes_view_v1, length) == 8, "bytes length");
NW_ASSERT(sizeof(nw_operation_callbacks_v1) == 24, "operation callbacks");
NW_ASSERT(offsetof(nw_operation_callbacks_v1, struct_size) == 0, "op size");
NW_ASSERT(offsetof(nw_operation_callbacks_v1, flags) == 4, "op flags");
NW_ASSERT(offsetof(nw_operation_callbacks_v1, cookie) == 8, "op cookie");
NW_ASSERT(offsetof(nw_operation_callbacks_v1, on_terminal) == 16, "op terminal");
NW_ASSERT(sizeof(nw_callbacks_v1) == 24, "callbacks");
NW_ASSERT(offsetof(nw_callbacks_v1, struct_size) == 0, "callback size");
NW_ASSERT(offsetof(nw_callbacks_v1, flags) == 4, "callback flags");
NW_ASSERT(offsetof(nw_callbacks_v1, cookie) == 8, "callback cookie");
NW_ASSERT(offsetof(nw_callbacks_v1, on_event) == 16, "callback function");
NW_ASSERT(NW_OK == 0 && NW_PENDING == 1 && NW_DOMAIN_ERROR == 13, "unchanged D08 statuses");
int main(void) {
    puts("{\"status\":\"passed\",\"scope\":\"design-only-x64-c-layout\",\"records\":5,\"product_execution\":false}");
    return 0;
}
