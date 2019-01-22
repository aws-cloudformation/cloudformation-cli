package com.aws.cfn.proxy;

import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
public class Credentials {
    private String accessKeyId;
    private String secretAccessKey;
    private String sessionToken;
}
