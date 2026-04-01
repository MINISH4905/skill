import torch
import time

def gpu_test():
    print("🔍 Checking GPU availability...\n")

    # Check CUDA
    if torch.cuda.is_available():
        print("✅ GPU is AVAILABLE")
        print(f"🔥 GPU Name: {torch.cuda.get_device_name(0)}")
        print(f"⚡ CUDA Version: {torch.version.cuda}")
        print(f"🧠 PyTorch Version: {torch.__version__}\n")

        device = torch.device("cuda")

        # Memory info
        print("📊 GPU Memory Info:")
        print(f"Total Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        print(f"Allocated: {torch.cuda.memory_allocated(0) / 1e9:.2f} GB")
        print(f"Reserved: {torch.cuda.memory_reserved(0) / 1e9:.2f} GB\n")

        # Create tensors
        print("⚙️ Running computation test...")
        size = 10000
        x = torch.rand(size, size, device=device)
        y = torch.rand(size, size, device=device)

        torch.cuda.synchronize()
        start = time.time()

        z = torch.matmul(x, y)

        torch.cuda.synchronize()
        end = time.time()

        print(f"⏱️ Time taken (GPU): {end - start:.4f} seconds")

        # Move back to CPU
        z_cpu = z.to("cpu")
        print("✅ Computation successful!\n")

    else:
        print("❌ GPU NOT AVAILABLE")
        print("➡️ Running on CPU instead...\n")

        device = torch.device("cpu")
        size = 3000
        x = torch.rand(size, size)
        y = torch.rand(size, size)

        start = time.time()
        z = torch.matmul(x, y)
        end = time.time()

        print(f"⏱️ Time taken (CPU): {end - start:.4f} seconds")

if __name__ == "__main__":
    gpu_test()
    