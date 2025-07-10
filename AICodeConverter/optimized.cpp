#include <iostream>
#include <iomanip>
#include <chrono>

// Optimized C++ function
double calculate(long long iterations, double param1, double param2) {
    double result = 1.0;
    for (long long i = 1; i <= iterations; ++i) {
        double j1 = i * param1 - param2;
        double j2 = i * param1 + param2;
        result -= 1.0 / j1;
        result += 1.0 / j2;
    }
    return result;
}

int main() {
    // Record start time
    auto start = std::chrono::high_resolution_clock::now();

    // Calculate result
    double result = calculate(100000000, 4, 1) * 4;

    // Record end time
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end - start;

    // Output results
    std::cout << std::fixed << std::setprecision(12);
    std::cout << "Result: " << result << "\n";
    std::cout << "Execution Time: " << elapsed.count() << " seconds\n";

    return 0;
}
