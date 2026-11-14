#ifndef NATIVEWEAVE_API_V1_H
#define NATIVEWEAVE_API_V1_H
/* Design-time canonical shared ABI declarations. No native product is implemented. */
#include <stdint.h>
#include <stddef.h>
#if defined(_WIN32)
# define NW_CDECL __cdecl
#else
# define NW_CDECL
#endif
#ifdef __cplusplus
extern "C" {
#endif

typedef uint32_t nw_status;
#define NW_OK UINT32_C(0)
#define NW_PENDING UINT32_C(1)
#define NW_CANCELED UINT32_C(2)
#define NW_INVALID_ARGUMENT UINT32_C(3)
#define NW_INVALID_STATE UINT32_C(4)
#define NW_OUT_OF_MEMORY UINT32_C(5)
#define NW_NOT_SUPPORTED UINT32_C(6)
#define NW_BUFFER_TOO_SMALL UINT32_C(7)
#define NW_CALLBACK_FAILED UINT32_C(8)
#define NW_NATIVE_PANIC UINT32_C(9)
#define NW_ENGINE_POISONED UINT32_C(10)
#define NW_CONTRACT_VIOLATION UINT32_C(11)
#define NW_TIMEOUT UINT32_C(12)
#define NW_DOMAIN_ERROR UINT32_C(13)

typedef struct nw_abi_info_v1 {
    uint32_t struct_size;
    uint32_t abi_major;
    uint32_t abi_minor;
    uint32_t pointer_width_bits;
    uint64_t capabilities;
    uint64_t reserved;
} nw_abi_info_v1;

typedef struct nw_error_info_v1 {
    uint32_t struct_size;
    uint32_t domain;
    int32_t code;
    uint32_t flags;
    uint64_t correlation_id;
} nw_error_info_v1;

typedef struct nw_bytes_view_v1 {
    const uint8_t *data;
    uint64_t length;
} nw_bytes_view_v1;

typedef nw_status (NW_CDECL *nw_on_terminal_fn)(
    uintptr_t cookie, uint32_t terminal_status,
    const nw_error_info_v1 *borrowed_error);

typedef struct nw_operation_callbacks_v1 {
    uint32_t struct_size;
    uint32_t flags;
    uintptr_t cookie;
    nw_on_terminal_fn on_terminal;
} nw_operation_callbacks_v1;

typedef nw_status (NW_CDECL *nw_on_event_fn)(
    uintptr_t cookie, uint32_t event_kind,
    const void *payload, uint64_t payload_bytes);

typedef struct nw_callbacks_v1 {
    uint32_t struct_size;
    uint32_t flags;
    uintptr_t cookie;
    nw_on_event_fn on_event;
} nw_callbacks_v1;

/* Every generated Engine supplies its own symbol with exactly this prototype.
   get_abi is mandatory; a get_api function table is not mandatory. */
typedef nw_status (NW_CDECL *nw_get_abi_v1_fn)(
    uint32_t requested_major, uint32_t out_capacity, nw_abi_info_v1 *out_info);

#ifdef __cplusplus
}
#endif
#endif
