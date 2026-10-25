//! Bounded, panic-contained ABI. All memory belongs to the caller.
use oozextract::Extractor;
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::slice;

const MAX_INPUT: usize = 64 * 1024 * 1024;
const MAX_OUTPUT: usize = 64 * 1024 * 1024;
const INVALID_ARGUMENT: i32 = 1;
const INVALID_STREAM: i32 = 2;
const SIZE_MISMATCH: i32 = 3;
const DECODER_PANIC: i32 = 4;

#[no_mangle]
pub extern "C" fn pukey_ui_decoder_abi() -> u32 {
    1
}

/// Returns 0 on success, 1 for invalid arguments, 2 for invalid compressed data,
/// 3 for an output size mismatch, and 4 if the Rust decoder panics.
/// Output must be ignored on every nonzero return; written is then zero.
///
/// # Safety
/// Non-null pointers must address live allocations of their stated lengths.
/// Input, output, and written must not overlap. written must be aligned and
/// writable. Output and written must not be accessed concurrently during the call.
#[no_mangle]
pub unsafe extern "C" fn pukey_ui_decompress(
    input: *const u8,
    input_len: usize,
    output: *mut u8,
    output_len: usize,
    written: *mut usize,
) -> i32 {
    if written.is_null() {
        return INVALID_ARGUMENT;
    }
    *written = 0;
    if input.is_null()
        || output.is_null()
        || input_len == 0
        || input_len > MAX_INPUT
        || output_len == 0
        || output_len > MAX_OUTPUT
    {
        return INVALID_ARGUMENT;
    }
    // Prevent constructing overlapping Rust slices even for accidental FFI misuse.
    let input_start = input as usize;
    let output_start = output as usize;
    let Some(input_end) = input_start.checked_add(input_len) else {
        return INVALID_ARGUMENT;
    };
    let Some(output_end) = output_start.checked_add(output_len) else {
        return INVALID_ARGUMENT;
    };
    if input_start < output_end && output_start < input_end {
        return INVALID_ARGUMENT;
    }
    let result = catch_unwind(AssertUnwindSafe(|| {
        let input = slice::from_raw_parts(input, input_len);
        let output = slice::from_raw_parts_mut(output, output_len);
        Extractor::new().read_from_slice(input, output)
    }));
    match result {
        Ok(Ok(count)) if count == output_len => {
            *written = count;
            0
        }
        Ok(Ok(_)) => SIZE_MISMATCH,
        Ok(Err(_)) => INVALID_STREAM,
        Err(_) => DECODER_PANIC,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn uncompressed_oodle_vector() {
        let mut input = vec![0x4c, 0x06];
        input.extend(std::iter::repeat_n(0xab, 0x40000));
        input.extend([0x4c, 0x06]);
        input.extend(std::iter::repeat_n(0xcd, 0x40000));
        let mut output = vec![0; 0x80000];
        let mut written = 0;
        let status = unsafe {
            pukey_ui_decompress(input.as_ptr(), input.len(), output.as_mut_ptr(),
                                output.len(), &mut written)
        };
        assert_eq!(status, 0);
        assert_eq!(written, output.len());
        assert!(output[..0x40000].iter().all(|&byte| byte == 0xab));
        assert!(output[0x40000..].iter().all(|&byte| byte == 0xcd));
    }

    #[test]
    fn truncated_oodle_is_an_error() {
        let input = [0x4c, 0x06, 0xab];
        let mut output = [0; 100];
        let mut written = 123;
        let status = unsafe {
            pukey_ui_decompress(input.as_ptr(), input.len(), output.as_mut_ptr(),
                                output.len(), &mut written)
        };
        assert_eq!(status, INVALID_STREAM);
        assert_eq!(written, 0);
    }
}
