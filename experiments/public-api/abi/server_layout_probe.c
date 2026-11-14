/* Compile-only-layout experiment; this does not implement or run a native Server. */
#include "nativeweave_server_api_v1.h"
#include <stdio.h>
_Static_assert(sizeof(void *) == 8, "initial Server profile is 64-bit");
_Static_assert(sizeof(nw_server_dispatch_v1) == 32, "dispatch v1 size");
_Static_assert(offsetof(nw_server_dispatch_v1, on_control) == 24, "control callback offset");
_Static_assert(sizeof(nw_server_listener_v1) == 120, "listener v1 size");
_Static_assert(offsetof(nw_server_listener_v1, name) == 40, "listener text view offset");
_Static_assert(sizeof(nw_server_config_v1) == 136, "config v1 size");
_Static_assert(offsetof(nw_server_config_v1, listeners) == 104, "listener array offset");
_Static_assert(sizeof(nw_server_route_v1) == 112, "route v1 size");
_Static_assert(offsetof(nw_server_route_v1, protocol_descriptor) == 96, "protocol metadata offset");
_Static_assert(sizeof(nw_server_request_info_v1) == 240, "request metadata v1 size");
_Static_assert(offsetof(nw_server_request_info_v1, trace_context) == 176, "trace view offset");
_Static_assert(offsetof(nw_server_request_info_v1, cancellation_status) == 236, "cancel snapshot offset");
_Static_assert(sizeof(nw_server_snapshot_v1) == 80, "counter snapshot v1 size");
_Static_assert(sizeof(nw_server_close_result_v1) == 32, "close observation v1 size");
_Static_assert(sizeof(nw_server_sse_event_v1) == 72, "SSE v1 size");
int main(void) {
    puts("{\"scope\":\"design-C-layout-only\",\"pointer_bits\":64,\"assertions\":15,\"passed\":true}");
    return 0;
}
